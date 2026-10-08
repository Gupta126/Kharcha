#!/usr/bin/env bash
# Laptop -> kh-core. Forwards the dev API (:8001) and mock ERP (:8090).
# The hosted demo is reached over HTTPS at https://$DOMAIN and needs no tunnel. Ctrl+C to stop.
set -euo pipefail
HOST=${1:-kh-core}
echo "Forwarding localhost:8001 and :8090 to $HOST (Ctrl+C to stop)"
exec ssh -N -o ExitOnForwardFailure=yes \
  -L 8001:127.0.0.1:8001 -L 8090:127.0.0.1:8090 "$HOST"
