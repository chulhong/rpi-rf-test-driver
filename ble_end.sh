#!/usr/bin/env bash
# Ends any ongoing LE test and prints packet count (if controller reports it)
set -euo pipefail
require_cmd(){ command -v "$1" >/dev/null 2>&1 || { echo "Missing: $1"; exit 1; }; }
require_cmd hcitool

OUT=$(sudo hcitool -i hci0 cmd 0x08 0x001F)
echo "$OUT"
# Attempt to grab last two bytes as packet count (implementation dependent)
COUNT_HEX=$(echo "$OUT" | awk '{print $NF}')
if [[ "$COUNT_HEX" =~ ^[0-9A-Fa-f]{2}$ ]]; then
  echo "Packet count (LSB byte): $((16#${COUNT_HEX}))"
fi
