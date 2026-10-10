#!/usr/bin/env bash
# Run the site on your own domain when the direct route to Cloudflare's tunnel edge does not
# work from this network.
#
#     ./run_with_domain_via_proxy.sh
#
# Why this exists: cloudflared dials Cloudflare's tunnel edge on TCP 7844, and on this
# network that direct route never completes a usable TLS handshake, so the connector never
# registers and the domain serves nothing. Going through the local v2rayN/xray proxy does
# complete it. cloudflared ignores HTTPS_PROXY for this connection, but it accepts a hidden
# `--edge` address, so this script starts a small relay on 127.0.0.1:7844, points
# cloudflared at that relay, and the relay forwards on to the edge through the proxy.
#
# The edge is a pool of addresses and not every one of them answers through the proxy (it
# changes from minute to minute), so a few are tried first and the first one that completes
# a TLS handshake is used. If none answers, the network is the problem and the script says
# so instead of leaving you with a silent hang.

set -euo pipefail

PROXY_PORT="${PROXY_PORT:-10810}"
RELAY_PORT=7844
PORT=8000
RELAY="$HOME/.cache/velingo_edge_relay.py"
RELAY_LOG=/tmp/lm_relay.log
CLOUDFLARED_LOG=/tmp/lm_cloudflared.log
CONFIG_FILE="$HOME/.cloudflared/config.yml"

cd "$(dirname "${BASH_SOURCE[0]}")"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared is not installed. Run ./setup_cloudflare_domain.sh once first." >&2
  exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
  echo "No $CONFIG_FILE yet, so there is no tunnel to run." >&2
  echo "Run ./setup_cloudflare_domain.sh once first." >&2
  exit 1
fi

# The proxy has to be up before any of this means anything. A quick CONNECT tells us.
# It is retried, because the proxy itself drops a request now and then -- one failed
# attempt would otherwise report "v2rayN is not running" while it is running fine.
proxy_answers() {
  timeout 8 curl -sS -x "http://127.0.0.1:$PROXY_PORT" -o /dev/null https://cloudflare.com/ 2>/dev/null
}

PROXY_OK=""
for _ in 1 2 3; do
  if proxy_answers; then
    PROXY_OK=yes
    break
  fi
  sleep 3
done

if [ -z "$PROXY_OK" ]; then
  echo "The proxy on 127.0.0.1:$PROXY_PORT is not answering (3 attempts)." >&2
  echo "Start v2rayN first, or pass a different port: PROXY_PORT=10808 $0" >&2
  exit 1
fi

# Find one edge address that actually completes a handshake through the proxy.
edge_answers() {
  timeout 5 openssl s_client -proxy "127.0.0.1:$PROXY_PORT" -connect "$1:7844" \
    -servername h2.cftunnel.com </dev/null 2>&1 | grep -q "Verify return code: 0"
}

EDGE=""
for candidate in \
  198.41.192.5 198.41.192.6 198.41.192.10 198.41.192.16 \
  198.41.192.26 198.41.192.35 198.41.192.42 198.41.192.47 \
  198.41.192.53 198.41.192.60 198.41.200.2 198.41.200.14 \
  198.41.200.20 198.41.200.35 198.41.200.49 198.41.200.55; do
  echo "  trying edge $candidate..."
  if edge_answers "$candidate"; then
    EDGE="$candidate"
    echo "  using edge $EDGE"
    break
  fi
done

if [ -z "$EDGE" ]; then
  echo "" >&2
  echo "No Cloudflare tunnel edge address answered through the proxy just now." >&2
  echo "That is a network property, not a setting: the edge is reachable through this" >&2
  echo "proxy only part of the time (measured: many addresses answer one minute, none the" >&2
  echo "next, while ordinary HTTPS through the same proxy keeps working)." >&2
  echo "Try again in a few minutes, or switch to another server in v2rayN." >&2
  exit 1
fi

# The relay is written out here rather than kept as a second file: it is 60 lines and this
# script is useless without it, so the two belong together.
mkdir -p "$(dirname "$RELAY")"
cat > "$RELAY" <<'PYTHON'
"""Forward cloudflared's edge connection through the local proxy.

cloudflared connects here instead of to Cloudflare directly (--edge 127.0.0.1:7844), and
each connection is opened on to the real edge through the proxy with an HTTP CONNECT.
"""
import os
import socket
import threading

LISTEN_HOST, LISTEN_PORT = "127.0.0.1", 7844
PROXY_HOST = "127.0.0.1"
PROXY_PORT = int(os.environ["PROXY_PORT"])
EDGE_HOST = os.environ["EDGE_HOST"]
EDGE_PORT = 7844
BUFFER_SIZE = 65536


def pump(source, target, remaining):
    try:
        while True:
            chunk = source.recv(BUFFER_SIZE)
            if not chunk:
                break
            target.sendall(chunk)
    except OSError:
        pass
    finally:
        try:
            target.shutdown(socket.SHUT_WR)
        except OSError:
            pass
        remaining[0] -= 1
        if remaining[0] == 0:
            for sock in (source, target):
                try:
                    sock.close()
                except OSError:
                    pass


def handle(client):
    try:
        upstream = socket.create_connection((PROXY_HOST, PROXY_PORT), timeout=20)
        upstream.settimeout(None)
    except OSError:
        client.close()
        return

    upstream.sendall(("CONNECT %s:%d HTTP/1.1\r\nHost: %s:%d\r\n\r\n" % (
        EDGE_HOST, EDGE_PORT, EDGE_HOST, EDGE_PORT)).encode("ascii"))

    header = b""
    while b"\r\n\r\n" not in header:
        chunk = upstream.recv(4096)
        if not chunk:
            client.close()
            upstream.close()
            return
        header += chunk

    if " 200" not in header.split(b"\r\n")[0].decode("ascii", "replace"):
        client.close()
        upstream.close()
        return

    remaining = [2]
    threading.Thread(target=pump, args=(client, upstream, remaining), daemon=True).start()
    pump(upstream, client, remaining)


def main():
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((LISTEN_HOST, LISTEN_PORT))
    server.listen(128)
    while True:
        client, _ = server.accept()
        threading.Thread(target=handle, args=(client,), daemon=True).start()


main()
PYTHON

TUNNEL_PID=""
RELAY_PID=""
stop_all() {
  [ -n "$TUNNEL_PID" ] && kill "$TUNNEL_PID" 2>/dev/null || true
  [ -n "$RELAY_PID" ] && kill "$RELAY_PID" 2>/dev/null || true
}
trap stop_all EXIT INT TERM

fuser -k "$RELAY_PORT/tcp" >/dev/null 2>&1 || true
PROXY_PORT="$PROXY_PORT" EDGE_HOST="$EDGE" .venv/bin/python "$RELAY" > "$RELAY_LOG" 2>&1 &
RELAY_PID=$!
sleep 1

TUNNEL_NAME=$(awk '/^tunnel:/ {print $2}' "$CONFIG_FILE")
echo "Starting the tunnel through the relay..."
cloudflared tunnel --no-autoupdate --protocol http2 --edge "127.0.0.1:$RELAY_PORT" \
  run "$TUNNEL_NAME" > "$CLOUDFLARED_LOG" 2>&1 &
TUNNEL_PID=$!

for _ in $(seq 1 10); do
  sleep 3
  if ! kill -0 "$TUNNEL_PID" 2>/dev/null; then break; fi
  if grep -q "Registered tunnel connection" "$CLOUDFLARED_LOG"; then
    echo "  tunnel connected through the proxy."
    break
  fi
done

if ! grep -q "Registered tunnel connection" "$CLOUDFLARED_LOG"; then
  echo "" >&2
  echo "The connector still did not register. Its log is $CLOUDFLARED_LOG and the relay's" >&2
  echo "is $RELAY_LOG. If the edge stopped answering between the check and the start, run" >&2
  echo "this script again." >&2
  exit 1
fi

ORIGIN=""
if [ -f .env ]; then
  ORIGIN=$(grep '^DJANGO_CSRF_TRUSTED_ORIGINS=' .env | head -1 | cut -d= -f2- || true)
fi

export DJANGO_DEBUG=False

echo "----------------------------------------------------------------"
echo "  Your site:   ${ORIGIN:-not set up yet}"
echo "  Local check: http://127.0.0.1:$PORT/"
echo ""
echo "  Served by this laptop through Cloudflare and the local proxy, so it"
echo "  only answers while this script, v2rayN and the laptop are running."
echo "  Press Ctrl+C to stop."
echo "----------------------------------------------------------------"

exec .venv/bin/python manage.py runserver "0.0.0.0:$PORT" --insecure
