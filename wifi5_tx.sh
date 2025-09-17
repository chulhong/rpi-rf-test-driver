#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"; require_cmd iperf3
PORT=5202; BIND=0.0.0.0; EXPECT=false
usage(){ echo "Usage: $0 [--port 5202] [--bind 0.0.0.0] [--expect-5]"; }
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) PORT="$2"; shift 2;;
    --bind) BIND="$2"; shift 2;;
    --expect-5) EXPECT=true; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown: $1"; usage; exit 1;;
  esac
done
$EXPECT && wifi_assert_band "5"
wifi_bump_txpower
echo "[INFO] iperf3 server on ${BIND}:${PORT} (Ctrl+C to stop)"
exec iperf3 -s -B "${BIND}" -p "${PORT}"
