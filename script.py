#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mac-side RF test driver for Raspberry Pi 4 (64-bit Lite) via serial console.
- No 'wl' required (uses hostapd/dnsmasq/iperf3/iw/bluez on RPi).
- Auto-detects single USB serial port if --port is omitted.
- RPi username/password can be set in-script (override via CLI).
- Mac IP auto-picks by priority: Wi-Fi -> Ethernet (else error).
"""

import argparse
import os
import sys
import time
import subprocess
import re
from pathlib import Path

import serial
import serial.tools.list_ports

# =========================
# Config: set here as default (can override via CLI)
# =========================
CONFIG_RPI_USER = "bella"
CONFIG_RPI_PASS = "bella"
CONFIG_AP_SSID  = "Bella-RF-Test"
CONFIG_AP_COUNTRY = "GB"   # adjust if needed
CONFIG_AP_SUBNET = None  # .1 used by RPi AP, DHCP .10-.200

PROMPT = r'[@~]# |[@~]\$ '
READ_TIMEOUT = 2.0
LONG_TIMEOUT = 20.0

# ---------- Serial helpers ----------
class SerialShell:
    def __init__(self, port, baud=115200, user=None, password=None, login_timeout=20):
        self.ser = serial.Serial(port=port, baudrate=baud, timeout=0.2)
        self.user = user
        self.password = password
        self.login_timeout = login_timeout

    def close(self):
        try:
            self.ser.close()
        except:
            pass

    def _read_all(self, timeout=READ_TIMEOUT):
        end = time.time() + timeout
        chunks = []
        while time.time() < end:
            b = self.ser.read(4096)
            if b:
                chunks.append(b)
            else:
                time.sleep(0.05)
        return b"".join(chunks)

    def _write_line(self, s):
        if not s.endswith("\n"):
            s += "\n"
        self.ser.write(s.encode("utf-8"))
        self.ser.flush()

    def login(self):
        # wake
        self._write_line("")
        out = self._read_all(timeout=2.0).decode(errors="ignore")

        if "login:" in out or "raspberrypi login:" in out:
            if not self.user or not self.password:
                raise RuntimeError("Login prompt detected: supply --user and --password or set in script.")
            self._write_line(self.user)
            time.sleep(0.5)
            self._read_all(timeout=1.0)
            self._write_line(self.password)
            time.sleep(1.0)
            self._read_all(timeout=self.login_timeout)

        # ensure shell
        self._write_line("echo __HELLO__ && (id || true)")
        self._read_all(timeout=1.0)

        # set recognizable PS1
        self._write_line("export PS1='PiRF# '")
        self._read_all(timeout=0.3)

    def run(self, cmd, timeout=LONG_TIMEOUT, check=True):
        marker = "__CMD_DONE__"
        wrapped = f"{cmd}; EC=$?; echo {marker}$EC"
        self._write_line(wrapped)
        out = b""
        end = time.time() + timeout
        while time.time() < end:
            chunk = self.ser.read(4096)
            if chunk:
                out += chunk
                if marker.encode() in out:
                    break
            else:
                time.sleep(0.05)
        txt = out.decode(errors="ignore")
        m = re.search(rf"{marker}(\-?\d+)", txt)
        rc = int(m.group(1)) if m else 0
        if check and rc != 0:
            raise RuntimeError(f"Remote command failed (rc={rc}): {cmd}\n---\n{txt}\n---")
        return txt, rc

# ---------- Mac helpers ----------
def ensure_iperf3():
    try:
        subprocess.check_call(["iperf3", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        print("WARNING: iperf3 not found on Mac. Install with: brew install iperf3", file=sys.stderr)
        return False

def run_local(cmd, **kwargs):
    print(f"[mac] $ {cmd}")
    return subprocess.Popen(cmd, shell=True, **kwargs)

def list_usb_serial_ports():
    ports = []
    for p in serial.tools.list_ports.comports():
        dev = p.device or ""
        # macOS typical USB serial device names:
        # /dev/tty.usbserial-*, /dev/tty.usbmodem*, /dev/tty.SLAB_USBtoUART, etc.
        if "/dev/cu.usb" in dev or dev.endswith("usbmodem") or "SLAB" in dev or "wchusbserial" in dev:
            ports.append(dev)
    return ports

def choose_serial_port(user_arg_port: str | None) -> str:
    if user_arg_port:
        return user_arg_port
    ports = list_usb_serial_ports()
    if len(ports) == 0:
        raise SystemExit("No USB serial devices found. Plug your USB-serial cable and/or specify --port.")
    if len(ports) > 1:
        msg = "Multiple USB serial devices found:\n  - " + "\n  - ".join(ports) + "\nPlease specify one with --port."
        raise SystemExit(msg)
    print(f"[auto] Using serial port: {ports[0]}")
    return ports[0]

def parse_networksetup_map():
    """
    Returns list of tuples: [(HardwarePort, Device), ...]
    """
    try:
        out = subprocess.check_output(["networksetup", "-listallhardwareports"], text=True)
    except Exception:
        return []
    lines = out.splitlines()
    pairs = []
    hp = dev = None
    for ln in lines:
        if ln.startswith("Hardware Port:"):
            hp = ln.split(":",1)[1].strip()
        elif ln.startswith("Device:"):
            dev = ln.split(":",1)[1].strip()
            if hp and dev:
                pairs.append((hp, dev))
                hp = dev = None
    return pairs

def ip_for_device(dev):
    try:
        ip = subprocess.check_output(["ipconfig", "getifaddr", dev], text=True).strip()
        return ip if ip else None
    except Exception:
        return None

def pick_mac_ip():
    """
    Priority: Wi-Fi -> Ethernet (first matching hardware port containing 'Ethernet')
    Returns (dev, ip)
    """
    pairs = parse_networksetup_map()
    # 1) Wi-Fi exact
    wifi_dev = None
    for hp, dev in pairs:
        if hp.lower() == "wi-fi" or hp.lower() == "wifi":
            wifi_dev = dev
            break
    if wifi_dev:
        ip = ip_for_device(wifi_dev)
        if ip:
            print(f"[auto] Using Mac Wi-Fi interface '{wifi_dev}' with IP {ip}")
            return wifi_dev, ip
    # 2) Ethernet-like (name contains 'Ethernet')
    eth_candidates = [dev for hp, dev in pairs if "ethernet" in hp.lower()]
    for dev in eth_candidates:
        ip = ip_for_device(dev)
        if ip:
            print(f"[auto] Using Mac Ethernet interface '{dev}' with IP {ip}")
            return dev, ip
    raise SystemExit("No active Wi-Fi/Ethernet IP found on Mac. Connect to a network and retry.")

def get_rpi_ip(sh: SerialShell):
    """
    Get RPI IP address with priority: WiFi -> Ethernet
    Returns IP address as string
    """
    # Try to get WiFi IP first
    try:
        out, _ = sh.run("ip addr show wlan0 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d'/' -f1", check=False)
        wifi_ip = out.strip()
        if wifi_ip and wifi_ip != "":
            print(f"[auto] Using RPI WiFi IP: {wifi_ip}")
            return wifi_ip
    except:
        pass
    
    # Try to get Ethernet IP
    try:
        out, _ = sh.run("ip addr show eth0 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d'/' -f1", check=False)
        eth_ip = out.strip()
        if eth_ip and eth_ip != "":
            print(f"[auto] Using RPI Ethernet IP: {eth_ip}")
            return eth_ip
        # Try alternative Ethernet interface names
        out, _ = sh.run("ip addr show | grep 'inet ' | grep -v '127.0.0.1' | grep -v '169.254' | awk '{print $2}' | cut -d'/' -f1 | head -1", check=False)
        alt_ip = out.strip()
        if alt_ip and alt_ip != "":
            print(f"[auto] Using RPI alternative interface IP: {alt_ip}")
            return alt_ip
    except:
        pass
    
    # If no IP found, raise error
    raise SystemExit("No active WiFi or Ethernet IP found on RPI. Check network connectivity and retry.")

# ---------- Remote (RPi) provisioning (no wl) ----------
INSTALL_SNIPPET = r"""
set -e
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update
sudo apt-get install -y hostapd dnsmasq iperf3 iw rfkill bluez bluez-hcidump python3

sudo mkdir -p /opt/rf-tests/emc
sudo chown -R $USER:$USER /opt/rf-tests

sudo systemctl stop hostapd || true
sudo systemctl stop dnsmasq || true
sudo systemctl stop wpa_supplicant || true

IFACE=$(iw dev | awk '/Interface/ {print $2; exit}')
if [ -z "$IFACE" ]; then IFACE=wlan0; fi
echo "$IFACE" | sudo tee /opt/rf-tests/.wifi_if >/dev/null
"""

LINK_MONITOR_PY = r"""#!/usr/bin/env python3
import subprocess, time, datetime, os
LOG = "/opt/rf-tests/emc/link_monitor.log"
peer_ip = os.environ.get("WIFI_PEER_IP")
def log(msg):
    ts = datetime.datetime.now().isoformat()
    print(msg, flush=True)
    with open(LOG, "a") as f:
        f.write(f"{ts} {msg}\n")
def ping(ip, count=3):
    try:
        subprocess.check_call(["ping", "-c", str(count), ip],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False
log("=== EMC link monitor start ===")
while True:
    if peer_ip:
        ok = ping(peer_ip, 3)
        log(f"WIFI_PING {peer_ip} {'OK' if ok else 'FAIL'}")
    time.sleep(2)
"""

# ---------- RPi state init/reset (safe to run anytime) ----------
RESET_SNIPPET = r"""
set -e
# 1) 중복 떠있는 프로세스 종료
sudo pkill hostapd || true
sudo pkill dnsmasq || true
sudo pkill iperf3 || true
sudo pkill -f link_monitor.py || true
sudo pkill -f l2ping || true

# 2) Wi-Fi 인터페이스 정리
IFACE=$(iw dev | awk '/Interface/ {print $2; exit}')
if [ -z "$IFACE" ]; then IFACE=wlan0; fi
sudo rfkill unblock all || true
sudo ip addr flush dev $IFACE || true
sudo ip link set $IFACE down || true

# wpa_supplicant 정리 (실험 중에는 우리가 올리는 AP가 우선)
sudo pkill wpa_supplicant || true

# 3) BLE/BT 정리
# BLE 테스트가 살아있다면 종료 시도
sudo btmgmt -i hci0 le-test-end >/dev/null 2>&1 || true
# HCI 리셋
sudo hciconfig hci0 down || true
sudo hciconfig hci0 up || true

# 4) 기본 네트워킹 서비스는 건드리지 않음 (dhcpcd 등)
# 필요 시 재부팅 없이 다음 시나리오가 바로 동작 가능한 깨끗한 상태로 만든다.
"""

def init_rpi_state(sh: SerialShell):
    """Make the Pi 'clean' before starting any scenario (except setup)."""
    sh.run(RESET_SNIPPET, timeout=30, check=False)

def push_link_monitor(sh: SerialShell):
    sh.run("mkdir -p /opt/rf-tests/emc")
    sh.run("cat > /opt/rf-tests/emc/link_monitor.py <<'PY'\n" + LINK_MONITOR_PY + "\nPY\nchmod +x /opt/rf-tests/emc/link_monitor.py")

# ---------- Hostapd/DHCP ephemeral bring-up ----------
def start_ap(sh: SerialShell, band="2g", channel="1", ssid=CONFIG_AP_SSID, country=CONFIG_AP_COUNTRY):
    print(f"[rpi] Start AP band={band} ch={channel} ssid={ssid}")
    sh.run("set -e; IFACE=$(cat /opt/rf-tests/.wifi_if 2>/dev/null || echo wlan0); "
           "sudo rfkill unblock all; sudo ip link set $IFACE down || true; sudo pkill wpa_supplicant || true; "
           "sudo ip addr flush dev $IFACE || true")

    if band == "2g":
        hw_mode = "g"
        ht_cap = "ieee80211n=1\nwmm_enabled=1\n"
        ch_line = f"channel={channel}"
    else:
        hw_mode = "a"
        ht_cap = "ieee80211n=1\nieee80211ac=1\nwmm_enabled=1\n"
        ch_line = f"channel={channel}"

    hostapd_conf = f"""
interface=$(cat /opt/rf-tests/.wifi_if 2>/dev/null || echo wlan0)
driver=nl80211
ssid={ssid}
country_code={country}
hw_mode={hw_mode}
{ch_line}
auth_algs=1
ignore_broadcast_ssid=0
wpa=0
{ht_cap}
"""
    sh.run("cat > /tmp/hostapd.conf <<'H'\n" + hostapd_conf + "\nH")

    sh.run("IFACE=$(cat /opt/rf-tests/.wifi_if 2>/dev/null || echo wlan0); "
           f"sudo ip link set $IFACE up; "
           f"sudo ip addr add {CONFIG_AP_SUBNET}.1/24 dev $IFACE || true")

    sh.run("cat > /tmp/dnsmasq.conf <<'D'\n"
           "interface=$(cat /opt/rf-tests/.wifi_if 2>/dev/null || echo wlan0)\n"
           "bind-interfaces\n"
           f"dhcp-range={CONFIG_AP_SUBNET}.10,{CONFIG_AP_SUBNET}.200,12h\n"
           "D\n")
    sh.run("sudo dnsmasq --conf-file=/tmp/dnsmasq.conf", timeout=5)
    sh.run("sudo hostapd -B /tmp/hostapd.conf", timeout=5)
    print("[rpi] AP up. Connect your Mac to SSID:", ssid)

def stop_ap(sh: SerialShell):
    sh.run("sudo pkill hostapd || true; sudo pkill dnsmasq || true; "
           "IFACE=$(cat /opt/rf-tests/.wifi_if 2>/dev/null || echo wlan0); "
           "sudo ip addr flush dev $IFACE || true; sudo ip link set $IFACE down || true")

# ---------- Wi-Fi scenarios ----------
def wait_for_mac_ip_on_selected_iface(target_subnet_prefix=None, timeout=60):
    """
    Poll Wi-Fi -> Ethernet for an IP, return (dev, ip).
    If target_subnet_prefix is given (e.g., '192.168.88'), require that prefix.
    """
    start = time.time()
    last_err = ""
    while time.time() - start < timeout:
        try:
            dev, ip = pick_mac_ip()
            if ip and (not target_subnet_prefix or ip.startswith(target_subnet_prefix + ".")):
                return dev, ip
            last_err = f"Found {dev} with IP {ip}, but not in {target_subnet_prefix}. Retrying..."
            print("[auto]", last_err)
        except SystemExit as e:
            last_err = str(e)
            print("[auto]", last_err)
        time.sleep(2)
    raise SystemExit(f"Failed to obtain suitable Mac IP in {timeout}s. Last: {last_err}")

def wifi_tx(sh: SerialShell, band, ch, duration):
    """
    Continuous modulated surrogate: UDP flood RPi->Mac over forced-channel AP.
    Mac IP auto-picked (Wi-Fi preferred).
    """
    init_rpi_state(sh)
    start_ap(sh, band=band, channel=ch)
    ensure_iperf3()
    print(f"[mac] Join the AP SSID '{CONFIG_AP_SSID}' (open).")
    # auto-pick Wi-Fi/Ethernet IP on Mac within AP subnet
    mac_dev, mac_ip = wait_for_mac_ip_on_selected_iface(CONFIG_AP_SUBNET)
    print(f"[auto] Using Mac {mac_dev} IP {mac_ip} for iperf3 server.")

    srv = run_local("iperf3 -s", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        cmd = f"iperf3 -c {mac_ip} -u -b 100M -t {duration}"
        print(f"[rpi] {cmd}")
        sh.run(cmd, timeout=duration+15, check=False)
    finally:
        srv.terminate()
        stop_ap(sh)

def wifi_rx(sh: SerialShell, band, ch, duration):
    """
    RPi receives traffic from Mac (Mac->RPi UDP flood).
    """
    init_rpi_state(sh)
    start_ap(sh, band=band, channel=ch)
    ensure_iperf3()
    print(f"[mac] Join the AP SSID '{CONFIG_AP_SSID}' (open).")
    # ensure Mac gets IP on this network (just for user info/logging)
    mac_dev, mac_ip = wait_for_mac_ip_on_selected_iface(CONFIG_AP_SUBNET)
    print(f"[auto] Mac {mac_dev} IP {mac_ip}")

    # RPi: iperf3 server
    sh.run("pkill iperf3 || true")
    sh.run("nohup iperf3 -s > /tmp/iperf3_srv.log 2>&1 &")

    # Get RPI IP address dynamically
    rpi_ip = get_rpi_ip(sh)
    
    # Mac: client -> RPi AP IP
    client = run_local(f"iperf3 -c {rpi_ip} -u -b 100M -t {duration}")
    client.wait(timeout=duration+15)

    out, _ = sh.run("iw dev $(cat /opt/rf-tests/.wifi_if 2>/dev/null || echo wlan0) station dump || true", check=False)
    print("\n[rpi] Station dump (RSSI etc.):\n", out)
    stop_ap(sh)

# ---------- BLE ----------
def ble_tx(sh: SerialShell, ch_sel):
    init_rpi_state(sh)
    ch = "0" if ch_sel == "low" else "39"
    cmds = [
        "sudo hciconfig hci0 down || true",
        "sudo hciconfig hci0 up",
        "sudo btmgmt -i hci0 power off || true",
        "sudo btmgmt -i hci0 le on",
        "sudo btmgmt -i hci0 power on",
        f"sudo btmgmt -i hci0 le-tx-test {ch} 37 0x00"
    ]
    for c in cmds: sh.run(c)
    print(f"[rpi] BLE LE TX test started on channel {ch}. Stop with 'ble_end'.")

def ble_rx(sh: SerialShell, ch_sel):    
    init_rpi_state(sh)
    ch = "0" if ch_sel == "low" else "39"
    cmds = [
        "sudo hciconfig hci0 down || true",
        "sudo hciconfig hci0 up",
        "sudo btmgmt -i hci0 power off || true",
        "sudo btmgmt -i hci0 le on",
        "sudo btmgmt -i hci0 power on",
        f"sudo btmgmt -i hci0 le-rx-test {ch}"
    ]
    for c in cmds: sh.run(c)
    print(f"[rpi] BLE LE RX test started on channel {ch}. Stop with 'ble_end'.")

def ble_end(sh: SerialShell):
    out, _ = sh.run("sudo btmgmt -i hci0 le-test-end", check=False)
    print("[rpi] BLE test end/counters:\n", out)

# ---------- BT Classic ----------
def btclassic_tx(sh: SerialShell, mac_bdaddr):
    init_rpi_state(sh)
    if not mac_bdaddr:
        raise SystemExit("Provide --mac-bt for BT Classic peer BD_ADDR.")
    cmds = [
        "sudo hciconfig hci0 up",
        f"sudo l2ping -i hci0 -s 1024 -f {mac_bdaddr}"
    ]
    print("[rpi] Starting BT Classic ACL flood (Ctrl+C on RPi to stop).")
    sh.run(cmds[0])
    sh.run(cmds[1], timeout=999999, check=False)

# ---------- EMC monitor ----------
LINK_MONITOR_WRAPPER = r"""
pkill -f link_monitor.py || true
nohup env WIFI_PEER_IP={peer} /usr/bin/python3 /opt/rf-tests/emc/link_monitor.py \
  >/opt/rf-tests/emc/monitor_stdout.log 2>&1 &
"""

def emc_monitor(sh: SerialShell, peer_ip, action="start"):
    if action == "start":
        init_rpi_state(sh)
    push_link_monitor(sh)
    if action == "start":
        sh.run(LINK_MONITOR_WRAPPER.format(peer=peer_ip), check=False)
        print("[rpi] EMC link monitor started. Log: /opt/rf-tests/emc/link_monitor.log")
    else:
        sh.run("pkill -f link_monitor.py || true")
        print("[rpi] EMC link monitor stopped.")

# ---------- Main ----------
def main():
    ap = argparse.ArgumentParser(description="Mac-side RF test driver for RPi4 via serial")
    ap.add_argument("--port", help="Serial device (e.g., /dev/tty.usbserial-xxxx). If omitted: auto if exactly one USB serial present.")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--user", help=f"RPi username (default from script: {CONFIG_RPI_USER})")
    ap.add_argument("--password", help=f"RPi password (default from script)")

    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup", help="Install prereqs on RPi (hostapd,dnsmasq,iperf3,bluez,iw)")
    sub.add_parser("recover", help="Initialize/clean RPi state (kill leftover hostapd/dnsmasq/iperf3/BLE tests, flush Wi-Fi iface)")

    p_tx24 = sub.add_parser("wifi_tx_24", help="2.4GHz TX (RPi->Mac). UDP flood with forced channel AP")
    p_tx24.add_argument("--ch", choices=["1","13"], default="1")
    p_tx24.add_argument("--duration", type=int, default=300)

    p_rx24 = sub.add_parser("wifi_rx_24", help="2.4GHz RX (Mac->RPi)")
    p_rx24.add_argument("--ch", choices=["1","13"], default="13")
    p_rx24.add_argument("--duration", type=int, default=300)

    p_tx5 = sub.add_parser("wifi_tx_5", help="5GHz TX (RPi->Mac)")
    p_tx5.add_argument("--ch", choices=["36","149"], default="36")
    p_tx5.add_argument("--duration", type=int, default=300)

    p_rx5 = sub.add_parser("wifi_rx_5", help="5GHz RX (Mac->RPi)")
    p_rx5.add_argument("--ch", choices=["36","149"], default="149")
    p_rx5.add_argument("--duration", type=int, default=300)

    p_ble_tx = sub.add_parser("ble_tx", help="BLE LE TX test")
    p_ble_tx.add_argument("--ch", choices=["low","high"], default="low")

    p_ble_rx = sub.add_parser("ble_rx", help="BLE LE RX test")
    p_ble_rx.add_argument("--ch", choices=["low","high"], default="high")

    sub.add_parser("ble_end", help="End BLE LE test and read counters")

    p_bt = sub.add_parser("btclassic_tx", help="BT Classic traffic flood to Mac (ACL)")
    p_bt.add_argument("--mac-bt", help="Mac Bluetooth BD_ADDR (XX:XX:XX:XX:XX:XX)", required=True)

    p_emc = sub.add_parser("emc_monitor", help="Start/stop EMC link monitor on RPi")
    p_emc.add_argument("--peer-ip", help="Peer IP to ping (Mac IP)", default=f"{CONFIG_AP_SUBNET}.10")
    p_emc.add_argument("--action", choices=["start","stop"], default="start")

    args = ap.parse_args()

    # choose serial port
    port = choose_serial_port(args.port)

    # username/password resolution
    user = args.user if args.user else CONFIG_RPI_USER
    password = args.password if args.password else CONFIG_RPI_PASS

    sh = SerialShell(port=port, baud=args.baud, user=user, password=password)
    try:
        sh.login()

        if args.cmd == "setup":
            print("[rpi] Installing prerequisites...")
            sh.run(INSTALL_SNIPPET, timeout=240)
            push_link_monitor(sh)
            print("[rpi] Setup done.")
            
        elif args.cmd == "recover":
            init_rpi_state(sh)
            print("[rpi] State recovered/initialized.")

        elif args.cmd == "wifi_tx_24":
            wifi_tx(sh, band="2g", ch=args.ch, duration=args.duration)

        elif args.cmd == "wifi_rx_24":
            wifi_rx(sh, band="2g", ch=args.ch, duration=args.duration)

        elif args.cmd == "wifi_tx_5":
            wifi_tx(sh, band="5g", ch=args.ch, duration=args.duration)

        elif args.cmd == "wifi_rx_5":
            wifi_rx(sh, band="5g", ch=args.ch, duration=args.duration)

        elif args.cmd == "ble_tx":
            ble_tx(sh, args.ch)

        elif args.cmd == "ble_rx":
            ble_rx(sh, args.ch)

        elif args.cmd == "ble_end":
            ble_end(sh)

        elif args.cmd == "btclassic_tx":
            btclassic_tx(sh, args.mac_bt)

        elif args.cmd == "emc_monitor":
            emc_monitor(sh, args.peer_ip, args.action)

        else:
            raise SystemExit("Unknown command")

    finally:
        sh.close()

if __name__ == "__main__":
    main()
