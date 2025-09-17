#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.env"

require_cmd(){ command -v "$1" >/dev/null 2>&1 || { echo "Missing: $1"; exit 1; }; }

wifi_assert_band(){
  # WARN if current association is not in the expected band
  local want="$1"  # "2.4" or "5"
  local freq
  freq=$(iw dev wlan0 link 2>/dev/null | awk '/freq:/{print $2}' || echo "")
  [[ -z "$freq" ]] && { echo "[WARN] wlan0 not associated."; return 0; }
  if [[ "$want" == "2.4" && "$freq" -ge 2400 && "$freq" -le 2500 ]]; then
    echo "[OK] Associated @ ${freq} MHz (2.4 GHz)."
  elif [[ "$want" == "5" && "$freq" -ge 4900 && "$freq" -le 5900 ]]; then
    echo "[OK] Associated @ ${freq} MHz (5 GHz)."
  else
    echo "[WARN] Associated @ ${freq} MHz; not in expected ${want} GHz band."
    echo "       (The external AP controls the channel/band; use separate SSIDs per band if needed.)"
  fi
}

wifi_bump_txpower(){
  [[ -z "${FORCE_TXPOWER_MBM:-}" ]] && return 0
  sudo ip link set wlan0 up || true
  sudo iw dev wlan0 set txpower fixed "${FORCE_TXPOWER_MBM}" || true
}

ble_reset(){
  sudo systemctl restart bluetooth
  sleep 1
  sudo hciconfig hci0 up
}
