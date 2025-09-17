#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"; require_cmd iperf3
MBPS="${UDP_MBPS_5}"; MAC="${MAC_IP}"; PORT=5202; EXPECT=false
usage(){ echo "Usage: $0 [--mac $MAC_IP] [--mbps $UDP_MBPS_5] [--port 5202] [--expect-5]"; }
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mac) MAC="$2"; shift 2;;
    --mbps) MBPS="$2"; shift 2;;
    --port) PORT="$2"; shift 2;;
    --expect-5) EXPECT=true; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown: $1"; usage; exit 1;;
  esac
done
$EXPECT && wifi_assert_band "5"
wifi_bump_txpower
echo "[INFO] Pi RX: sending UDP client to $MAC:${PORT} @ ${MBPS} Mbps"
exec iperf3 -u -b "${MBPS}"M -t 0 -c "${MAC}" -p "${PORT}"
