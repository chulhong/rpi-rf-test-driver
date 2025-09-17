#!/usr/bin/env bash
# Params: --channel <0..39|lower|upper>
set -euo pipefail
source "$(dirname "$0")/common.sh"; require_cmd hcitool; require_cmd btmgmt

CH="lower"
usage(){ echo "Usage: $0 [--channel 0..39|lower|upper]   (End+read count: ./ble_end.sh)"; }
while [[ $# -gt 0 ]]; do
  case "$1" in
    --channel) CH="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown: $1"; usage; exit 1;;
  esac
done
if [[ "$CH" == "lower" ]]; then CH=0; elif [[ "$CH" == "upper" ]]; then CH=39; fi
[[ "$CH" =~ ^[0-9]+$ ]] || { echo "Bad channel: $CH"; exit 1; }

ble_reset
sudo btmgmt -i hci0 power off
sudo btmgmt -i hci0 le on
sudo btmgmt -i hci0 connectable off
sudo btmgmt -i hci0 bondable off
sudo btmgmt -i hci0 power on

printf -v CHX "%02x" "$CH"
echo "[INFO] LE RX: ch=$CH (RF: $((2402+2*CH)) MHz). End with ./ble_end.sh"
exec sudo hcitool -i hci0 cmd 0x08 0x001D "$CHX"
