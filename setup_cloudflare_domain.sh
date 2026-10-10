#!/usr/bin/env bash
# Point a domain you own at this laptop, using a named Cloudflare Tunnel.
#
#     ./setup_cloudflare_domain.sh
#
# Run this once. It walks you through the parts that can only be done in a browser --
# Cloudflare's dashboard and DNSHE's console -- and does the parts that can be scripted:
# installing cloudflared, running the tunnel, and writing the Django settings it needs.
#
# Why a tunnel instead of just pointing DNS at the laptop: this laptop is on a mobile
# hotspot behind carrier-grade NAT, so the internet cannot open a connection to it at all.
# The tunnel reverses the direction -- cloudflared dials OUT to Cloudflare and keeps that
# connection open, and Cloudflare sends the traffic back down it.
#
# There are no secrets in this file. The tunnel token is typed in hidden and written only
# to .env, which is gitignored.

set -euo pipefail

ENV_FILE=".env"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

TOTAL_STAGES=7
CURRENT_STAGE=0

DOMAIN=""
TUNNEL_TOKEN=""
PUBLIC_HOSTNAME=""

# ----------------------------------------------------------------------- helpers ---
# Not indented into functions on purpose: everything below is one procedure, and the
# stages read top to bottom like a checklist.

stage() {
  CURRENT_STAGE=$((CURRENT_STAGE + 1))
  clear
  printf '\n\033[1;36m[%s/%s] %s\033[0m\n' "$CURRENT_STAGE" "$TOTAL_STAGES" "$1"
  printf '%s\n\n' "------------------------------------------------------------------------"
}

say()  { printf '%s\n' "$1"; }
step() { printf '  \033[1m%s\033[0m %s\n' "->" "$1"; }

open_url() {
  printf '  Opening %s\n' "$1"
  (xdg-open "$1" >/dev/null 2>&1 &) || true
}

ask() {
  local label="$1" answer=""
  printf '  %s: ' "$label" >&2
  read -r answer
  printf '%s' "$answer"
}

ask_secret() {
  local label="$1" answer=""
  printf '  %s: ' "$label" >&2
  read -rs answer
  printf '\n' >&2
  printf '%s' "$answer"
}

# Write KEY=VALUE into .env, replacing the line if it is already there. Values are written
# unquoted, the way the rest of the file is.
write_env() {
  local key="$1" value="$2"
  touch "$ENV_FILE"
  if grep -q "^${key}=" "$ENV_FILE"; then
    # `|` as the delimiter because the value is a URL full of slashes.
    sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
  else
    printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
  fi
  printf '  wrote %s to .env\n' "$key"
}

confirm() {
  local prompt="$1" answer=""
  printf '  %s [y/N] ' "$prompt" >&2
  read -r answer
  case "$answer" in
    y|Y|yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

pause() {
  printf '\n  Press Enter when you are ready to continue...'
  read -r _
}

# ============================================================ stage 1: the domain ===

stage "Your domain"
say "This must be the domain you registered, written in full."
say "For example, if you registered 'sina' under a domain you own, it is sina.example.com."
say ""
say "NOT one of DNSHE's free suffixes: de5.net, us.ci and cc.cd are all blocked by"
say "Iranian ISPs, so a domain under them is invisible to visitors here. That is not a"
say "Cloudflare problem and nothing in this script can work around it."
say ""
DOMAIN=$(ask "Your domain")

if [ -z "$DOMAIN" ]; then
  say "No domain given. Stopping." >&2
  exit 1
fi

say ""
say "Checking that it is usable..."

# A domain can be real, delegated and still open to nobody: the national DNS filter answers
# a fixed sinkhole address instead of the real one for the names it blocks. 10.10.34.34 and
# 10.10.34.36 are those two addresses -- twitter.com gets the same answer from here. Worth
# checking now, because the alternative is waiting on nameserver propagation for a domain
# that no Iranian ISP will resolve.
#
# ahostsv4, not `getent hosts`: for some blocked names the filter stitches the sinkhole into
# an IPv6 address instead (twitter.com answers 2001:4188:2:600:10:10:34:36) and `getent hosts`
# prints that IPv6 form, which the comparison below would not recognise.
RESOLVED_IP=$(getent ahostsv4 "$DOMAIN" 2>/dev/null | awk 'NR==1 {print $1}' || true)

if [ "$RESOLVED_IP" = "10.10.34.34" ] || [ "$RESOLVED_IP" = "10.10.34.36" ]; then
  say ""
  say "STOP: $DOMAIN answers with $RESOLVED_IP, which is the DNS filter's sinkhole."
  say "This name is blocked inside Iran, so the address would not open for you or for"
  say "anyone else here -- whatever Cloudflare and DNSHE are told to do."
  say ""
  say "Every free DNSHE suffix is on that list (de5.net, us.ci, cc.cd). Pick a domain that"
  say "resolves to a real address, then run this again:"
  say "    getent hosts yourdomain.tld"
  exit 1
fi

if [ -n "$RESOLVED_IP" ]; then
  say "  $DOMAIN resolves to $RESOLVED_IP."
else
  say "  $DOMAIN does not resolve yet. That is normal for a brand new registration;"
  say "  carry on, and the check at the end will confirm it."
fi

# ================================================= stage 2: add it to Cloudflare ===

stage "Add the domain to Cloudflare"
say "Cloudflare has to be given the domain before it can hand you nameservers."
say ""
step "In the dashboard that is about to open, choose 'Add a site'."
step "Type your domain exactly: $DOMAIN"
step "Pick the 'Free' plan."
step "Cloudflare now shows TWO nameservers, like ada.ns.cloudflare.com"
step "Leave that page open -- you need them in the next stage."
pause
open_url "https://dash.cloudflare.com/"

say ""
say "Back in this terminal:"
NAMESERVERS=$(ask "Paste the two Cloudflare nameservers, space separated")
say ""
say "Them: $NAMESERVERS"

# ================================================== stage 3: nameservers at DNSHE =

stage "Point DNSHE at Cloudflare"
say "Your registrar has to be told to use Cloudflare's nameservers."
say "DNSHE supports this; it is the same thing as 'hosting the domain elsewhere'."
say ""
step "In the DNSHE console that opens, find the domain: $DOMAIN"
step "Look for the DNS / Nameserver settings."
step "Replace whatever nameservers are there with the two Cloudflare ones."
pause
open_url "https://my.dnshe.com/"

say ""
say "Changing nameservers takes time to spread -- usually minutes, sometimes hours."
say "Cloudflare has to see the change before anything else will work, so let us wait"
say "for it here rather than guessing."
say ""

# Cloudflare is the authority here, not us: its dashboard shows the domain as "Active"
# once it has taken over. This lookup is only a hint, and it is deliberately not allowed
# to block the wizard -- on a filtered network an NS query can come back empty even when
# the delegation is live (measured on this very domain: the parent zone answers A records
# while its NS query returns NOERROR with an empty answer). A couple of attempts for the
# happy path, then the human decides.
ATTEMPT=1
LIVE_NS=""
while [ "$ATTEMPT" -le 8 ]; do
  LIVE_NS=$(dig +short NS "$DOMAIN" 2>/dev/null | tr '\n' ' ' || true)
  if printf '%s' "$LIVE_NS" | grep -qi cloudflare; then
    say "  Cloudflare's nameservers are visible from here already."
    break
  fi
  printf '  checking... %s/8  (seen so far: %s)\n' "$ATTEMPT" "${LIVE_NS:-nothing}"
  ATTEMPT=$((ATTEMPT + 1))
  sleep 15
done

if ! printf '%s' "$LIVE_NS" | grep -qi cloudflare; then
  say ""
  say "Not visible from this machine yet -- which does NOT mean it failed. An NS lookup"
  say "can come back empty here even when the delegation is working."
  say ""
  say "The answer that counts is in Cloudflare's dashboard for $DOMAIN:"
  say "   Pending  -> still waiting on the nameservers. This can take a few hours."
  say "   Active   -> Cloudflare has taken over. Carry on."
  say ""
  if ! confirm "Does Cloudflare say Active?"; then
    say "Wait for it to say Active, then run this script again -- re-running is safe," >&2
    say "and it will pick up from the same place." >&2
    exit 1
  fi
fi

# ================================================ stage 4: create the tunnel ======

stage "Create the tunnel and copy its token"
say "A 'tunnel' is the outbound connection your laptop will keep open to Cloudflare."
say ""
step "This opens Cloudflare Zero Trust -- a different dashboard from the last one."
step "Go to Networks > Tunnels, and choose 'Create a tunnel'."
step "Choose the 'Cloudflared' connector type."
step "Name it anything, for example: gambegam-laptop"
step "On the next screen Cloudflare shows an install command containing a long token"
step "that starts with 'eyJ'. Copy ONLY that token, not the whole command."
pause
open_url "https://one.dash.cloudflare.com/"

say ""
TUNNEL_TOKEN=$(ask_secret "Paste the tunnel token (input is hidden)")

if [ -z "$TUNNEL_TOKEN" ]; then
  say "No token given. Stopping." >&2
  exit 1
fi
say "Got a token of ${#TUNNEL_TOKEN} characters."

# ========================================== stage 5: install and start cloudflared ==

stage "Install cloudflared and start the service"
say "This is the program that holds the connection open to Cloudflare."
say "You chose to install it as a system service, so it will start on its own at boot."
say "Installing needs your password -- sudo will ask you right here."
say ""

DEB=/tmp/cloudflared-linux-amd64.deb
if command -v cloudflared >/dev/null 2>&1; then
  say "cloudflared is already installed; skipping the download."
else
  say "Downloading cloudflared..."
  curl -fsSL -o "$DEB" \
    "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb"
  say "  downloaded $(du -h "$DEB" | cut -f1)"

  sudo dpkg -i "$DEB"
fi

say ""
say "Registering the service with your tunnel token (sudo again)..."
sudo cloudflared service install "$TUNNEL_TOKEN"

say ""
say "Waiting for the tunnel to report healthy..."
for _ in $(seq 1 20); do
  sleep 3
  STATUS=$(sudo cloudflared tunnel info 2>/dev/null | head -5 || true)
  if [ -n "$STATUS" ]; then
    say "$STATUS"
    break
  fi
done

# ================================================ stage 6: publish the hostname ====

stage "Publish the site on your domain"
say "Now the tunnel needs to be told WHICH domain name it answers for."
say ""
step "Go back to the Cloudflare Zero Trust tab and open your tunnel."
step "Open the 'Routes' tab, then 'Add route', and choose 'Published application'."
step "Hostname: a subdomain and your domain from the drop-down. Using no subdomain"
step "  means the bare $DOMAIN, which is what you want if you have nothing else there."
step "Service URL: http://localhost:8000   (your Django server, on this laptop)"
step "Choose 'Add route'. Cloudflare creates the DNS record for you."
pause
open_url "https://one.dash.cloudflare.com/"

say ""
PUBLIC_HOSTNAME=$(ask "The hostname you just published, in full")

if [ -z "$PUBLIC_HOSTNAME" ]; then
  PUBLIC_HOSTNAME="$DOMAIN"
fi
say "Your site will be at: https://$PUBLIC_HOSTNAME"

# ============================================ stage 7: tell Django and verify it ===

stage "Point Django at the domain and check it"
say "Django refuses requests whose Host it does not recognise, and it rejects form"
say "posts whose Origin it does not trust. Both now need to know your domain."
say ""

# DJANGO_DEBUG is deliberately NOT written here. Your .env keeps DEBUG on for local
# work, and the two run scripts export DEBUG=False for the hosted case instead -- a shell
# variable beats the file, which is how config/settings.py is built. Writing False into
# .env would silently take the debug pages away from your own development.
write_env "DJANGO_SERVE_MEDIA" "True"
write_env "DJANGO_ALLOWED_HOSTS" "localhost,127.0.0.1,$DOMAIN,$PUBLIC_HOSTNAME"
write_env "DJANGO_CSRF_TRUSTED_ORIGINS" "https://$PUBLIC_HOSTNAME"

say ""
say "Starting Django so we can test the whole chain..."
DJANGO_DEBUG=False .venv/bin/python manage.py runserver 0.0.0.0:8000 --insecure > /tmp/lm_domain_server.log 2>&1 &
DJANGO_PID=$!
sleep 5

say ""
say "Requesting https://$PUBLIC_HOSTNAME/ through Cloudflare..."
CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 40 "https://$PUBLIC_HOSTNAME/" || true)

say ""
if [ "$CODE" = "200" ] || [ "$CODE" = "302" ]; then
  say "  \033[1;32mIt works.\033[0m https://$PUBLIC_HOSTNAME/ answered $CODE."
else
  say "  Got '$CODE' instead of 200/302."
  say ""
  say "  The usual causes, in order of likelihood:"
  say "   - Cloudflare still says 'Pending' for the domain (nameservers not spread yet)"
  say "   - the route's Service URL is not http://localhost:8000"
  say "   - the tunnel shows as Down in the dashboard"
  say ""
  say "  Wait a few minutes and run this last check again with:"
  say "     curl -I https://$PUBLIC_HOSTNAME/"
fi

say ""
say "Django is running now (pid $DJANGO_PID) as a foreground test."
say "For normal use, start it with ./run_with_domain.sh instead."
say ""
say "----------------------------------------------------------------"
say "  Your site:  https://$PUBLIC_HOSTNAME"
say "  It is served by THIS laptop through Cloudflare, so it is reachable"
say "  from anywhere -- but only while this laptop is awake and online."
say "----------------------------------------------------------------"
