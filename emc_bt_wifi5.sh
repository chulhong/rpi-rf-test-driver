#!/usr/bin/env bash
# Runs BT Classic SPP stream + iperf3 server for 5 GHz traffic.
set -euo pipefail
source "$(dirname "$0")/common.sh"; require_cmd sdptool; require_cmd rfcomm; require_cmd iperf3; require_cmd dd

wifi_assert_band "5" || true
wifi_bump_txpower

# Launch BT SPP streamer in background
bash "$(dirname "$0")/btclassic_tx.sh" --chunk 1024 &
BT_PID=$!

PORT=5204
trap 'kill $BT_PID 2>/dev/null || true' EXIT
echo "[INFO] BT Classic streaming + iperf3 server on ${PORT} (Ctrl+C to stop)"
exec iperf3 -s -p "${PORT}"
