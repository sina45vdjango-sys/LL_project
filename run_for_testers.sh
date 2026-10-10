#!/usr/bin/env bash
# Run the project so other people on this network can open it and give feedback.
#
#     ./run_for_testers.sh
#
# This is a local run, not a deployment: `runserver` is behind it, so keep it on a
# network you trust and do not forward the port to the internet. The README section
# "Letting other people try it, on your own network" explains why each setting below
# is needed — leaving any one of them out fails quietly rather than loudly.

set -euo pipefail

PORT=8000

# The address this machine uses to reach the rest of the network. Asking the routing
# table is what keeps Docker's bridge address (172.17.0.1) out of the answer, which is
# the one people cannot reach. The fallback is for a machine with no default route.
HOST_IP=$(ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \K[\d.]+' || true)
if [ -z "$HOST_IP" ]; then
  HOST_IP=$(ip -4 addr show scope global | grep -oP 'inet \K[\d.]+' | grep -v '^172\.17\.' | head -1)
fi

if [ -z "$HOST_IP" ]; then
  echo "Could not work out this machine's network address. Are you connected?" >&2
  exit 1
fi

export DJANGO_DEBUG=False        # otherwise a 500 shows testers your settings and secrets
export DJANGO_SERVE_MEDIA=True   # otherwise every audio file 404s
export DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1,$HOST_IP"   # otherwise every request is 400

echo "----------------------------------------------------------------"
echo "  Tell them to open:   http://$HOST_IP:$PORT/"
echo ""
echo "  They must be on the same network as this laptop."
echo "  If it does not load for them, allow the port once:"
echo "      sudo ufw allow $PORT/tcp"
echo ""
echo "  Database: the mirror (language_learning_mirror), so their accounts"
echo "  and attempts stay out of your real data."
echo "  Press Ctrl+C to stop."
echo "----------------------------------------------------------------"

# 0.0.0.0 — listen on every interface, or nobody else can connect.
# --insecure — serve /static/ even though DEBUG is off.
exec .venv/bin/python manage.py runserver "0.0.0.0:$PORT" --insecure
