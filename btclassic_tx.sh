#!/usr/bin/env bash
# BT Classic SPP TX on RFCOMM ch 1, race-free.
# Uses 'rfcomm listen' in background and a loop that waits for /dev/rfcomm0,
# then streams zeros until the peer disconnects. Then it loops and waits again.

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "[BT-TX] Elevating to root..."
  exec sudo -E bash "$0" "$@"
fi

CHUNK="${CHUNK:-1024}"

RFCOMM=$(command -v rfcomm)
SDPTOOL=$(command -v sdptool)
HCICONFIG=$(command -v hciconfig)
SYSTEMCTL=$(command -v systemctl)
STTY=$(command -v stty)
DD=$(command -v dd)
SLEEP=$(command -v sleep)

echo "[BT-TX] Starting SPP TX on RFCOMM ch 1 (chunk=${CHUNK})."

$SYSTEMCTL restart bluetooth
$HCICONFIG hci0 up || true
/sbin/modprobe rfcomm 2>/dev/null || true

# Advertise Serial Port Profile
$SDPTOOL add SP >/dev/null 2>&1 || true

# Clean any stale binding
$RFCOMM release 0 2>/dev/null || true

# Start a persistent listener in the background
# It keeps /dev/rfcomm0 present and accepts incoming connections on ch 1.
$RFCOMM listen 0 1 >/dev/null 2>&1 &
LISTEN_PID=$!
trap 'kill $LISTEN_PID 2>/dev/null || true; $RFCOMM release 0 2>/dev/null || true' EXIT

echo "[BT-TX] Waiting for connections on channel 1…"

while true; do
  # Wait until /dev/rfcomm0 exists
  for _ in $(seq 1 100); do
    [[ -e /dev/rfcomm0 ]] && break
    $SLEEP 0.05
  done
  if [[ ! -e /dev/rfcomm0 ]]; then
    echo "[BT-TX] rfcomm device not created; restarting listener…"
    kill $LISTEN_PID 2>/dev/null || true
    $RFCOMM listen 0 1 >/dev/null 2>&1 & LISTEN_PID=$!
    continue
  fi

  # Configure TTY (ignore errors if not ready yet)
  $STTY -F /dev/rfcomm0 115200 cs8 -cstopb -parenb -ixon -ixoff -crtscts || true

  echo "[BT-TX] Peer connected. Streaming to /dev/rfcomm0 …"
  # This blocks while connected; exits when peer disconnects
  if ! $DD if=/dev/zero of=/dev/rfcomm0 bs="${CHUNK}" status=none; then
    echo "[BT-TX] Stream ended (disconnect)."
  fi

  # Release device so we can accept a clean next connection
  $RFCOMM release 0 2>/dev/null || true
  echo "[BT-TX] Waiting for next connection…"
done

