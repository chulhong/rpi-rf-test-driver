#!/usr/bin/env bash
# Pi acts as iperf3 client receiving UDP from the Mac (server).
# Params: --mac <IP> --mbps <N> --port <p> --expect-24
set -euo pipefail
source "$(dirname "$0")/common.sh"; require_cmd iperf3

MBPS="${UDP_MBPS_24}"
MAC="${MAC_IP}"
PORT=5201
EXPECT=false

usage(){ echo "Usage: $0 [--mac $MAC_IP] [--mbps $UDP_MBPS_24] [--port 5201] [--expect-24]"; }
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mac) MAC="$2"; shift 2;;
    --mbps) MBPS="$2"; shift 2;;
    --port) PORT="$2"; shift 2;;
    --expect-24) EXPECT=true; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown: $1"; usage; exit 1;;
  esac
done

$EXPECT && wifi_assert_band "2.4"
wifi_bump_txpower
echo "[INFO] Pi->Mac (RX on Pi). Sending UDP client to $MAC:${PORT} @ ${MBPS} Mbps (0=forever)"
exec iperf3 -u -b "${MBPS}"M -t 0 -c "${MAC}" -p "${PORT}"
