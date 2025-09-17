# RPi RF Test Driver

A comprehensive test suite for RF compliance testing on Raspberry Pi, supporting BLE, Bluetooth Classic, Wi-Fi 2.4 GHz, and Wi-Fi 5 GHz radios. This toolset enables automated testing for various regulatory standards including EN 300 328, EN 301 893, FCC 15 C/E, RSS-247, and EMC requirements.

## Overview

This test driver provides scripts to control RF radios in both TX (transmit) and RX (receive) modes, enabling continuous modulated transmission at maximum power for compliance testing. The system supports individual radio testing as well as simultaneous multi-radio operation for EMC testing scenarios.

## Supported Standards

### EN 300 328 (2.4 GHz ISM Band)
- **BLE**: Lower channel (2402 MHz) and upper channel (2480 MHz)
- **Bluetooth Classic**: SPP streaming for continuous transmission
- **Wi-Fi 2.4 GHz**: Continuous UDP traffic generation

### EN 301 893 (5 GHz Band)
- **Wi-Fi 5 GHz**: Lower and upper channel testing with continuous transmission

### FCC 15 C/E, RSS-247
- Individual radio testing with TX transmissions on specified channels
- Continuous modulated transmission at maximum power

### EMC Testing
- Simultaneous multi-radio operation for reduced test time
- Communication link monitoring during immunity tests
- Error detection capabilities during RF interference testing

## Prerequisites

### Hardware
- Raspberry Pi with integrated Wi-Fi and Bluetooth
- Additional Raspbery Pi for BT classic traffic generation/reception
- External test equipment (Mac or PC) for Wi-Fi traffic generation/reception
- Lab Wi-Fi network for Wi-Fi testing

### System Requirements
- Linux-based system (tested on Raspberry Pi OS)
- Root/sudo access for hardware control
- Network connectivity for Wi-Fi testing

## One-Time Setup

Before running any tests, perform the following one-time setup on your Raspberry Pi:

### 1. Update System and Install Dependencies
```bash
# Update package lists and install required tools
sudo apt-get update
sudo apt-get install -y hostapd dnsmasq iw iproute2 iptables-persistent \
  tcpdump rfkill bluez bluez-hcidump iperf3 git unzip
```

### 2. Configure Services
```bash
# Ensure services are disabled by default (we'll start/stop explicitly)
sudo systemctl disable hostapd || true
sudo systemctl disable dnsmasq || true
```

### 3. Set Regulatory Domain
```bash
# Set regulatory domain (ETSI Germany; change if needed for your region)
echo "REGDOMAIN=FI" | sudo tee /etc/default/crda
sudo iw reg set FI
```

**Note**: Change `DE` to your appropriate country code:
- `US` - United States (FCC)
- `FI` - Finland (ETSI)
- `GB` - United Kingdom (ETSI)
- `CA` - Canada (ISED)
- See `iw reg get` for available regions

### 4. Deploy Test Scripts
```bash
git clone git@github.com:chulhong/rpi-rf-test-driver.git
```

### Software Dependencies Installed
The setup installs the following tools required by the test scripts:
- `hcitool` - Bluetooth Low Energy control
- `btmgmt` - Bluetooth management interface
- `rfcomm` - Bluetooth Classic RFCOMM support
- `sdptool` - Bluetooth service discovery
- `iperf3` - Network traffic generation
- `iw` - Wi-Fi interface control
- `hostapd` - Wi-Fi access point functionality
- `dnsmasq` - DNS and DHCP services
- `tcpdump` - Network packet analysis
- `bluez` - Bluetooth stack

## Mac/PC Test Equipment Setup

For Wi-Fi testing, you'll need a Mac or PC to act as the traffic generator/receiver. Follow these setup instructions:

### Mac Setup

#### 1. Install iperf3
```bash
# Using Homebrew (recommended)
brew install iperf3

# Alternative: Using MacPorts
sudo port install iperf3

# Verify installation
iperf3 --version
```

#### 2. Configure Network
- Connect Mac to the same lab Wi-Fi network as the Raspberry Pi
- (Optional) Note the Mac's IP address (used in `config.env` as `MAC_IP`)
- Ensure firewall allows iperf3 traffic on ports 5201-5204

#### 3. Test Network Connectivity
```bash
# Test connectivity to Raspberry Pi
ping <PI_IP_ADDRESS>

# Test iperf3 connectivity (run this after starting Pi server)
iperf3 -c <PI_IP_ADDRESS> -p 5201 -t 10
```

### Windows PC Setup

#### 1. Install iperf3
```bash
# Using Chocolatey
choco install iperf3

# Using Scoop
scoop install iperf3

# Or download from: https://iperf.fr/iperf-download.php
```

#### 2. Configure Network
- Connect PC to the same lab Wi-Fi network as the Raspberry Pi
- (Optional) Note the PC's IP address (used in `config.env` as `MAC_IP`)
- Configure Windows Firewall to allow iperf3 traffic

#### 3. Test Network Connectivity
```cmd
# Test connectivity to Raspberry Pi
ping <PI_IP_ADDRESS>

# Test iperf3 connectivity
iperf3 -c <PI_IP_ADDRESS> -p 5201 -t 10
```

### Linux PC Setup

#### 1. Install iperf3
```bash
# Ubuntu/Debian
sudo apt-get install iperf3

# CentOS/RHEL/Fedora
sudo yum install iperf3
# or
sudo dnf install iperf3

# Arch Linux
sudo pacman -S iperf3
```

#### 2. Configure Network
- Connect PC to the same lab Wi-Fi network as the Raspberry Pi
- (Optional) Note the PC's IP address (used in `config.env` as `MAC_IP`)
- Configure firewall if needed

#### 3. Test Network Connectivity
```bash
# Test connectivity to Raspberry Pi
ping <PI_IP_ADDRESS>

# Test iperf3 connectivity
iperf3 -c <PI_IP_ADDRESS> -p 5201 -t 10
```

## (Optional) Configuration

Edit `config.env` to match your test environment:

```bash
# Country code for regulatory compliance
COUNTRY=FI

# Test equipment IP address (Mac/PC on lab network)
MAC_IP=10.0.2.201

# UDP traffic rates (adjust based on network capacity)
UDP_MBPS_24=100    # 2.4 GHz band
UDP_MBPS_5=400     # 5 GHz band

# Optional: Force Wi-Fi TX power (uncomment and adjust)
# FORCE_TXPOWER_MBM=2000   # 20 dBm
```

### Finding IP Addresses

To configure the `MAC_IP` setting, you need to determine the IP addresses of your test equipment:

#### On Mac (Test Equipment)
```bash
# Get Mac's IP address
ipconfig getifaddr en0
```

#### On Raspberry Pi (Test Device)
```bash
# Get Raspberry Pi's IP address
hostname -I | awk '{print $1}'

# Get Raspberry Pi's Bluetooth MAC address
hciconfig hci0 | grep "BD Address"
```

#### Example Configuration
```bash
# If Mac IP is 192.168.1.100 and Pi IP is 192.168.1.50
MAC_IP=192.168.1.100

# Example Bluetooth MAC address: DC:A6:32:12:34:56
# Use this for btclassic_rx.sh --peer parameter
```

### Bluetooth Classic Pairing Setup

For Bluetooth Classic testing, you need two Raspberry Pis - one as TX (transmitter) and one as RX (receiver). They must be paired and trusted in advance:

#### 1. On TX Pi (Server/Transmitter)
```bash
bluetoothctl
power on
agent on
default-agent
pairable on
discoverable on
quit
```

#### 2. On RX Pi (Client/Receiver)
```bash
bluetoothctl
power on
agent on
default-agent
scan on
# Wait for TX Pi to appear, then note its address (e.g., 2C:CF:67:A4:E9:49)
pair 2C:CF:67:A4:E9:49
trust 2C:CF:67:A4:E9:49
connect 2C:CF:67:A4:E9:49   # optional test connection
quit
```

#### 3. Verify Pairing
```bash
# On RX Pi, check paired devices
bluetoothctl devices

# Test connection (optional)
bluetoothctl connect 2C:CF:67:A4:E9:49
```

**Note**: Replace `2C:CF:67:A4:E9:49` with the actual Bluetooth MAC address of your TX Pi. Use the `hciconfig hci0 | grep "BD Address"` command to find the TX Pi's address.

## Script Reference

### BLE (Bluetooth Low Energy) Testing

#### `ble_tx.sh` - BLE Transmit Mode
```bash
./ble_tx.sh [--channel 0..39|lower|upper] [--length 37] [--pattern 0..7]
```
- **Purpose**: Continuous BLE transmission for radiated spurious measurements
- **Channels**: `lower` (2402 MHz), `upper` (2480 MHz), or specific channel 0-39
- **Patterns**: 0=PRBS9, 1=11110000, 2=10101010, 3-7=vendor-defined
- **Usage**: `./ble_tx.sh --channel lower --pattern 0`

#### `ble_rx.sh` - BLE Receive Mode
```bash
./ble_rx.sh [--channel 0..39|lower|upper]
```
- **Purpose**: BLE reception monitoring for communication link testing
- **Usage**: `./ble_rx.sh --channel upper`

#### `ble_end.sh` - End BLE Test
```bash
./ble_end.sh
```
- **Purpose**: Terminates ongoing BLE test and reports packet count
- **Usage**: Run after `ble_rx.sh` to get reception statistics

### Bluetooth Classic Testing

#### `btclassic_tx.sh` - BT Classic Transmit
```bash
./btclassic_tx.sh [--chunk 1024]
```
- **Purpose**: Continuous SPP data streaming for radiated spurious measurements
- **Operation**: Waits for RFCOMM connection, then streams continuous data
- **Usage**: `./btclassic_tx.sh --chunk 2048`

#### `btclassic_rx.sh` - BT Classic Receive
```bash
./btclassic_rx.sh --peer <BT_ADDR> [--channel 1] [--outfile /dev/null]
```
- **Purpose**: Connects to BT Classic SPP server and receives continuous data
- **Usage**: `./btclassic_rx.sh --peer DC:A6:32:12:34:56 --outfile /tmp/spp_dump.bin`

### Wi-Fi 2.4 GHz Testing

#### `wifi24_tx.sh` - Wi-Fi 2.4 GHz Transmit
```bash
./wifi24_tx.sh [--port 5201] [--bind 0.0.0.0] [--expect-24]
```
- **Purpose**: iperf3 server for continuous 2.4 GHz transmission
- **Operation**: Pi acts as server, Mac/PC runs client to generate traffic
- **Usage**: `./wifi24_tx.sh --expect-24`

#### `wifi24_rx.sh` - Wi-Fi 2.4 GHz Receive
```bash
./wifi24_rx.sh [--mac <IP>] [--mbps 100] [--port 5201] [--expect-24]
```
- **Purpose**: iperf3 client receiving UDP traffic from Mac/PC
- **Usage**: `./wifi24_rx.sh --mac 10.0.2.201 --mbps 100 --expect-24`

### Wi-Fi 5 GHz Testing

#### `wifi5_tx.sh` - Wi-Fi 5 GHz Transmit
```bash
./wifi5_tx.sh [--port 5202] [--bind 0.0.0.0] [--expect-5]
```
- **Purpose**: iperf3 server for continuous 5 GHz transmission
- **Usage**: `./wifi5_tx.sh --expect-5`

#### `wifi5_rx.sh` - Wi-Fi 5 GHz Receive
```bash
./wifi5_rx.sh [--mac <IP>] [--mbps 400] [--port 5202] [--expect-5]
```
- **Purpose**: iperf3 client receiving UDP traffic on 5 GHz
- **Usage**: `./wifi5_rx.sh --mac 10.0.2.201 --mbps 400 --expect-5`

### EMC Testing Scripts

#### `emc_ble_wifi24.sh` - BLE + Wi-Fi 2.4 GHz Simultaneous
```bash
./emc_ble_wifi24.sh
```
- **Purpose**: Simultaneous BLE advertising and Wi-Fi 2.4 GHz traffic
- **Operation**: High-duty BLE advertising + iperf3 server on port 5203
- **Usage**: For EMC immunity testing with dual-radio operation

#### `emc_bt_wifi5.sh` - BT Classic + Wi-Fi 5 GHz Simultaneous
```bash
./emc_bt_wifi5.sh
```
- **Purpose**: Simultaneous BT Classic SPP streaming and Wi-Fi 5 GHz traffic
- **Operation**: BT Classic streaming + iperf3 server on port 5204
- **Usage**: For EMC immunity testing with dual-radio operation

## Test Procedures

### EN 300 328 Compliance Testing

1. **BLE Testing**:
   ```bash
   # Lower channel (2402 MHz)
   ./ble_tx.sh --channel lower --pattern 0
   
   # Upper channel (2480 MHz)
   ./ble_tx.sh --channel upper --pattern 0
   ```

2. **Bluetooth Classic Testing**:
   ```bash
   # Start SPP streaming
   ./btclassic_tx.sh --chunk 1024
   ```

3. **Wi-Fi 2.4 GHz Testing**:
   ```bash
   # Start server (Pi side)
   ./wifi24_tx.sh --expect-24
   
   # Start client (Mac/PC side)
   iperf3 -u -b 100M -t 0 -c <PI_IP> -p 5201
   ```

### EN 301 893 Compliance Testing

1. **Wi-Fi 5 GHz Testing**:
   ```bash
   # Start server (Pi side)
   ./wifi5_tx.sh --expect-5
   
   # Start client (Mac/PC side)
   iperf3 -u -b 400M -t 0 -c <PI_IP> -p 5202
   ```

### EMC Testing

1. **BLE + Wi-Fi 2.4 GHz**:
   ```bash
   ./emc_ble_wifi24.sh
   ```

2. **BT Classic + Wi-Fi 5 GHz**:
   ```bash
   ./emc_bt_wifi5.sh
   ```

## Monitoring and Validation

### Communication Link Monitoring
- **BLE**: Use `ble_rx.sh` + `ble_end.sh` to monitor packet reception
- **BT Classic**: Monitor RFCOMM connection status and data flow
- **Wi-Fi**: Monitor iperf3 statistics for throughput and packet loss

### Error Detection
- Monitor for connection drops during immunity tests
- Check packet loss rates during RF interference
- Validate continuous transmission without gaps

## Troubleshooting

### Common Issues

1. **Bluetooth Not Responding**:
   ```bash
   sudo systemctl restart bluetooth
   sudo hciconfig hci0 up
   ```

2. **Wi-Fi Band Mismatch**:
   - Use `--expect-24` or `--expect-5` flags to verify correct band
   - Check AP configuration for separate 2.4/5 GHz SSIDs

3. **Permission Denied**:
   - Ensure scripts have execute permissions: `chmod +x *.sh`
   - Run with sudo for hardware control operations

4. **Network Connectivity**:
   - Verify `MAC_IP` in `config.env` matches test equipment
   - Check firewall settings for iperf3 ports (5201-5204)

### Performance Tuning

- Adjust `UDP_MBPS_24` and `UDP_MBPS_5` in `config.env` based on network capacity
- Modify `--chunk` size in BT Classic scripts for optimal throughput
- Use `FORCE_TXPOWER_MBM` to set specific Wi-Fi power levels

## Safety and Compliance Notes

- Ensure all testing is performed in appropriate RF test chambers
- Follow local regulatory requirements for RF testing
- Use proper RF shielding and measurement equipment
- Document all test parameters and results for compliance reporting

## License

This software is provided for RF compliance testing purposes. Ensure compliance with local regulations and standards when using for certification testing.
