# RPI RF Test Driver

A Python-based automation script for RF certification testing on Raspberry Pi 4, enabling comprehensive Wi-Fi, Bluetooth, and EMC compliance testing via USB serial control from macOS.

## Features

- **Wi-Fi 2.4 GHz Testing**: TX/RX operations on low and high channels using hostapd + iperf3
- **Wi-Fi 5 GHz Testing**: TX/RX operations on low and high channels with DFS channel support
- **Bluetooth Low Energy (BLE)**: TX/RX testing using btmgmt commands
- **Bluetooth Classic**: Continuous traffic generation using l2ping flood mode
- **EMC Link Monitoring**: Ping-based peer device connectivity during immunity testing
- **Auto-detection**: Mac IP address and serial port automatic detection
- **Cross-platform Control**: Mac-based script controlling Pi 4 via USB serial connection

## Prerequisites

### Hardware Requirements
- **Mac**: macOS-compatible computer with USB ports
- **Raspberry Pi 4**: Model B with 2GB+ RAM, 64-bit Lite OS
- **USB Type-C Cable**: For serial communication between Mac and Pi
- **RF Test Equipment**: Compatible with certification standards (EN 300 328, EN 301 893, FCC, RSS-247, EMC)

### Software Requirements

#### Mac
- Python 3.7+
- pyserial library
- Network connectivity (Wi-Fi or Ethernet)

#### Raspberry Pi 4
- Raspberry Pi OS Lite (64-bit)
- hostapd
- dnsmasq
- iperf3
- iw (wireless tools)
- rfkill
- bluez (Bluetooth stack)
- python3

## Setup Instructions

### Mac Setup

1. **Install Python Dependencies**
   ```bash
   pip3 install pyserial
   ```

2. **Install System packages**
   ```bash
   brew install iperf3
   ```

3. **Verify USB Serial Access**
   ```bash
   ls /dev/cu.*
   ls /dev/tty.*
   ```

### Raspberry Pi Setup

1. **Update System**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Install Required Packages**
   ```bash
   sudo apt install -y hostapd dnsmasq iperf3 wireless-tools rfkill bluez python3
   ```

3. **Enable Services**
   ```bash
   sudo systemctl enable hostapd
   sudo systemctl enable dnsmasq
   sudo systemctl enable bluetooth
   ```

4. **Configure USB Serial**
   ```bash
   sudo raspi-config
   # Navigate to: Interface Options > Serial Port
   # Enable serial interface, disable serial console
   ```

5. **Perform Setup**

Run the following script on Mac

```bash
python script.py setup
```

### Bluetooth pairing

#### Make RPI discoverable and pairable

```bash
bluetoothctl
```

On `bluetoothctl` prompt, do the following.
```
[bluetooth]# power on
[bluetooth]# agent on
[bluetooth]# default-agent
[bluetooth]# discoverable on
[bluetooth]# pairable on
```

#### Pair with raspeberry pi on Mac

* System Settings -> Bluetooth
* Pair with Raspberry Pi


# Usage Instructions

## EN300.328 Radiated Spurious Measurements

### Wi-Fi 2.4 GHz Testing

#### TX Mode (Low Channel)
```bash
python3 script.py wifi_tx_24 --ch 1 --duration 300
```

### TX Mode (High Channel)
```bash
python3 script.py wifi_tx_24 --ch 13 --duration 300
```

#### RX Mode (Low Channel)
```bash
python3 script.py wifi_rx_24 --ch 1 --duration 300
```

#### RX Mode (High Channel)
```bash
python3 script.py wifi_rx_24 --ch 13 --duration 300
```

### BLE Testing












### Wi-Fi 5 GHz Testing

#### TX Mode (Low Channel)
```bash
python3 rpi_rf_test_driver.py --wifi-5 --mode tx --channel low
```

#### RX Mode (High Channel)
```bash
python3 rpi_rf_test_driver.py --wifi-5 --mode rx --channel high
```

### Bluetooth Testing

#### BLE TX/RX
```bash
python3 rpi_rf_test_driver.py --ble --mode tx
python3 rpi_rf_test_driver.py --ble --mode rx
```

#### BT Classic Continuous Traffic
```bash
python3 rpi_rf_test_driver.py --bt-classic --mode flood
```

### EMC Link Monitoring

```bash
python3 rpi_rf_test_driver.py --emc --peer-ip 192.168.1.100
```

### Combined Testing Scenarios

#### Full Wi-Fi Certification Suite
```bash
python3 rpi_rf_test_driver.py --wifi-24 --wifi-5 --mode tx --channel both
```

#### Bluetooth Compliance Testing
```bash
python3 rpi_rf_test_driver.py --ble --bt-classic --mode both
```

## Notes and Limitations

- **No wl Support**: This script does not use Broadcom's `wl` utility. All Wi-Fi operations use standard Linux tools (hostapd, iw, rfkill).
- **DFS Channel Caution**: 5 GHz DFS channels may require regulatory domain configuration and channel availability checks.
- **BT Classic Limitations**: Vendor-specific commands are not supported. Only standard HCI and L2CAP operations are available.
- **Serial Port Priority**: The script prefers `/dev/cu.*` devices when multiple serial ports are detected.
- **IP Detection Priority**: Mac IP address detection follows: Wi-Fi > Ethernet > Other interfaces.
- **Continuous Modulation**: For compliance testing requiring continuous modulation, ensure proper iperf3 parameters and network stability.

## FAQ

### Q: How does the script detect my Mac's IP address?
**A**: The script automatically detects your Mac's IP address with priority: Wi-Fi interface first, then Ethernet. This IP is used for peer device communication during RX/TX testing.

### Q: Why does the script prefer `/dev/cu.*` over `/dev/tty.*`?
**A**: `/dev/cu.*` devices provide callout (dialout) functionality which is more reliable for serial communication control. The script will use `/dev/tty.*` if no `/dev/cu.*` devices are available.

### Q: How do I ensure continuous modulation compliance for certification?
**A**: Use the `--continuous` flag with appropriate iperf3 parameters. Ensure stable network conditions and monitor for packet loss during extended testing periods.

### Q: Can I run multiple test scenarios simultaneously?
**A**: The script supports combined testing modes (e.g., `--wifi-24 --wifi-5`) but runs them sequentially to avoid resource conflicts and ensure accurate measurements.

### Q: What if my Pi doesn't have the required packages?
**A**: The setup script will attempt to install missing packages. Ensure your Pi has internet connectivity and sufficient storage space (at least 1GB free).

### Q: How do I troubleshoot serial connection issues?
**A**: Check USB cable connection, verify Pi serial interface is enabled, and ensure no other applications are using the serial port. Use `ls /dev/cu.*` to verify device detection.

## Support

For technical support or feature requests, please refer to the project repository or contact the development team.

---

**Note**: This tool is designed for RF certification testing in controlled laboratory environments. Ensure compliance with local regulations and testing standards before use.
