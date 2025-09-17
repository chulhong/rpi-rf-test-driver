#!/usr/bin/env bash
# Params: --chunk <bytes> (per write)
set -euo pipefail
source "$(dirname "$0")/common.sh"; require_cmd sdptool; require_cmd rfcomm; require_cmd dd

CHUNK=1024
usage(){ echo "Usage: $0 [--chunk 1024]   (Pair Mac->Pi, connect to SPP, stream runs)"; }
while [[ $# -gt 0 ]]; do
  case "$1" in
    --chunk) CHUNK="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown: $1"; usage; exit 1;;
  esac
done

sudo systemctl restart bluetooth
sudo hciconfig hci0 up
sudo sdptool add SP

# When a client connects to RFCOMM ch 1, stream zeros indefinitely
echo "[INFO] Waiting for RFCOMM connection on channel 1…"
while true; do
  rfcomm watch rfcomm0 1 "sh -c 'stty -F /dev/rfcomm0 115200 cs8 -cstopb -parenb -ixon -ixoff -crtscts; dd if=/dev/zero of=/dev/rfcomm0 bs=${CHUNK} status=none'"
done
