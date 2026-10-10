#!/usr/bin/env bash
# Run the site on your own domain. Use this after setup_cloudflare_domain.sh has been run
# once.
#
#     ./run_with_domain.sh
#
# cloudflared runs as a system service, so the tunnel is already up -- this script only
# starts Django, which is the half that a reboot does not restart for you.
#
# The domain settings (ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, SERVE_MEDIA) live in .env,
# written there by the setup script. DEBUG is exported here instead of being written to
# .env, so that plain `manage.py runserver` keeps your debug pages while this script runs
# the site the way a visitor sees it. A shell variable beats the file -- see
# config/settings.py.

set -euo pipefail

PORT=8000
cd "$(dirname "${BASH_SOURCE[0]}")"

# Whatever hostname the setup script published is the one to show. Read it back out of
# .env rather than asking again, so the two cannot drift apart.
ORIGIN=""
if [ -f .env ]; then
  ORIGIN=$(grep '^DJANGO_CSRF_TRUSTED_ORIGINS=' .env | head -1 | cut -d= -f2- || true)
fi

if fuser "$PORT/tcp" >/dev/null 2>&1; then
  echo "Port $PORT is already in use. Stop whatever is on it first:" >&2
  echo "    fuser -k $PORT/tcp" >&2
  exit 1
fi

# This script starts the tunnel itself. It used to assume a systemd service named
# cloudflared -- which is what `sudo cloudflared service install` creates. On this machine
# cloudflared lives in the user's home (~/.local/bin) with its credentials in ~/.cloudflared,
# so no such service exists, so the script's service check always failed, and the tunnel was never started:
# the site answered on the laptop and nowhere else. Running it from here also means the tunnel
# stops when this script stops, which is the right behaviour for a test session.
TUNNEL_PID=""

stop_tunnel() {
  if [ -n "$TUNNEL_PID" ]; then
    kill "$TUNNEL_PID" 2>/dev/null || true
  fi
}
trap stop_tunnel EXIT INT TERM

CLOUDFLARED_LOG=/tmp/lm_cloudflared.log
CONFIG_FILE="$HOME/.cloudflared/config.yml"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared is not installed. Run ./setup_cloudflare_domain.sh once to install it." >&2
  echo "(continuing -- the site will work on this machine but not on its domain)" >&2
elif [ ! -f "$CONFIG_FILE" ]; then
  echo "No $CONFIG_FILE yet, so there is no tunnel to run. Run ./setup_cloudflare_domain.sh" >&2
  echo "once to create it. (continuing on this machine only)" >&2
else
  TUNNEL_NAME=$(awk '/^tunnel:/ {print $2}' "$CONFIG_FILE")
  echo "Starting the tunnel ($TUNNEL_NAME)..."

  # QUIC is attempted first by default and is blocked on this network (UDP 7844), which
  # leaves cloudflared sitting in its precheck before it gives up. http2 uses TCP 7844, which
  # does work, so it is requested outright instead of waiting for the fallback.
  cloudflared tunnel --no-autoupdate --protocol http2 run "$TUNNEL_NAME" > "$CLOUDFLARED_LOG" 2>&1 &
  TUNNEL_PID=$!

  # "Started" is not "connected": if the edge never registers this connector, every visitor
  # gets a hang and nothing in Django's log explains it. Say so here instead, and name the
  # one cause that is not fixable from this laptop.
  for _ in $(seq 1 10); do
    sleep 3
    if ! kill -0 "$TUNNEL_PID" 2>/dev/null; then break; fi
    if grep -q "Registered tunnel connection" "$CLOUDFLARED_LOG"; then
      echo "  tunnel connected."
      break
    fi
  done

  if ! grep -q "Registered tunnel connection" "$CLOUDFLARED_LOG"; then
    echo "" >&2
    echo "The tunnel did not register a connection. Its log is at $CLOUDFLARED_LOG." >&2
    echo "If it sits at 'Connecting via http2' forever, the network is blocking Cloudflare's" >&2
    echo "tunnel range -- not something this script can fix. The network has to change." >&2
    echo "" >&2
  fi
fi

export DJANGO_DEBUG=False

echo "----------------------------------------------------------------"
echo "  Your site:   ${ORIGIN:-not set up yet -- run ./setup_cloudflare_domain.sh}"
echo "  Local check: http://127.0.0.1:$PORT/"
echo ""
echo "  Served by this laptop through Cloudflare, so it only answers while"
echo "  this laptop is awake and this script is running."
echo "  Press Ctrl+C to stop."
echo "----------------------------------------------------------------"

exec .venv/bin/python manage.py runserver "0.0.0.0:$PORT" --insecure
