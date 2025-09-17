#!/usr/bin/env bash
# Starts high-duty BLE advertising + iperf3 server for 2.4 GHz traffic.
set -euo pipefail
source "$(dirname "$0")/common.sh"; require_cmd btmgmt; require_cmd iperf3

wifi_assert_band "2.4" || true
wifi_bump_txpower

# BLE high-duty non-connectable advertising
ble_reset
sudo btmgmt -i hci0 power off
sudo btmgmt -i hci0 le on
sudo btmgmt -i hci0 connectable off
sudo btmgmt -i hci0 power on
sudo btmgmt -i hci0 adv on

PORT=5203
echo "[INFO] BLE advertising ON + iperf3 server on ${PORT} (Ctrl+C to stop)"
exec iperf3 -s -p "${PORT}"
