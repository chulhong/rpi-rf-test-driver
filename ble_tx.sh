#!/usr/bin/env bash
# Params: --channel <0..39|lower|upper>  --length <1..255>  --pattern <0..7>
# Defaults: lower=0 (2402 MHz), upper=39 (2480 MHz), length=37 (0x25), pattern=0 (PRBS9)
set -euo pipefail
source "$(dirname "$0")/common.sh"; require_cmd hcitool; require_cmd btmgmt

CH="lower"; LEN=37; PAT=0
usage(){ cat <<USAGE
Usage: $0 [--channel 0..39|lower|upper] [--length 37] [--pattern 0..7]
Patterns: 0=PRBS9, 1=11110000, 2=10101010, 3..7=vendor-defined
End test (and read count if RX) with: sudo hcitool -i hci0 cmd 0x08 0x001F
USAGE
}
while [[ $# -gt 0 ]]; do
  case "$1" in
    --channel) CH="$2"; shift 2;;
    --length) LEN="$2"; shift 2;;
    --pattern) PAT="$2"; shift 2;;
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
printf -v LENX "%02x" "$LEN"
printf -v PATX "%02x" "$PAT"

echo "[INFO] LE TX: ch=$CH (RF: $((2402+2*CH)) MHz), len=$LEN, pattern=$PAT"
exec sudo hcitool -i hci0 cmd 0x08 0x001E "$CHX" "$LENX" "$PATX"
