#!/usr/bin/env bash
# Connect to a BT Classic SPP server and sink data (continuous RX).
# Usage:
#   ./btclassic_rx.sh --peer <BT_ADDR> [--channel 1] [--outfile /dev/null]
# Examples:
#   ./btclassic_rx.sh --peer DC:A6:32:12:34:56
#   ./btclassic_rx.sh --peer DC:A6:32:12:34:56 --outfile /tmp/spp_dump.bin

set -euo pipefail

PEER=""
CHAN=1
OUT="/dev/null"

usage() {
  echo "Usage: $0 --peer <BT_ADDR> [--channel 1] [--outfile /dev/null]"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --peer) PEER="$2"; shift 2;;
    --channel) CHAN="$2"; shift 2;;
    --outfile) OUT="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

[[ -z "$PEER" ]] && { echo "Missing --peer <BT_ADDR>"; usage; exit 1; }

require_cmd(){ command -v "$1" >/dev/null 2>&1 || { echo "Missing: $1"; exit 1; }; }
require_cmd rfcomm
require_cmd sdptool
require_cmd stty
require_cmd dd

echo "[INFO] Preparing Bluetooth..."
sudo systemctl restart bluetooth
sudo hciconfig hci0 up

# Clean old binding if any
sudo rfcomm release 0 || true

echo "[INFO] Connecting to $PEER channel $CHAN..."
# This creates /dev/rfcomm0 on success and stays in foreground; we’ll run it in background.
sudo rfcomm connect 0 "$PEER" "$CHAN" &
RFC_PID=$!

# Wait for device node
for _ in {1..30}; do
  [[ -e /dev/rfcomm0 ]] && break
  sleep 0.2
done
[[ -e /dev/rfcomm0 ]] || { echo "[ERR] /dev/rfcomm0 not created"; kill $RFC_PID 2>/dev/null || true; exit 2; }

# TTY tuning (not strictly required but keeps it clean)
sudo stty -F /dev/rfcomm0 115200 cs8 -cstopb -parenb -ixon -ixoff -crtscts

echo "[INFO] Connected. Sinking data to $OUT (Ctrl+C to stop)…"
trap 'echo "[INFO] Cleaning up..."; sudo rfcomm release 0 || true; kill $RFC_PID 2>/dev/null || true' EXIT

# Sink bytes forever (shows rate every few seconds if you add status=progress)
sudo dd if=/dev/rfcomm0 of="$OUT" bs=4096 status=progress