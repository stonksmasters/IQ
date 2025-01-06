import subprocess
from bleak import BleakScanner
import asyncio

def detect_wifi():
    """
    Scans for nearby Wi-Fi networks and returns a list of dictionaries
    containing SSID and signal strength.
    """
    networks = []
    try:
        result = subprocess.run(["iwlist", "wlan0", "scan"], capture_output=True, text=True)
        output = result.stdout
        cells = output.split("Cell")
        for cell in cells[1:]:
            ssid_line = [line for line in cell.split("\n") if "ESSID" in line]
            signal_line = [line for line in cell.split("\n") if "Signal level" in line]
            if ssid_line and signal_line:
                ssid = ssid_line[0].split(":")[1].strip().strip('"')
                signal = signal_line[0].split("=")[1].strip().split(" ")[0]
                networks.append({"SSID": ssid, "signal": signal})
    except Exception as e:
        print(f"Wi-Fi detection error: {e}")
    return networks


def detect_bluetooth():
    """
    Scans for Bluetooth Low Energy (BLE) devices and returns a list of found devices.
    """
    async def scan_devices():
        devices = []
        try:
            discovered_devices = await BleakScanner.discover()
            for device in discovered_devices:
                devices.append({
                    "name": device.name or "Unknown",
                    "address": device.address,
                    "rssi": device.rssi  # Directly access rssi attribute
                })
        except Exception as e:
            print(f"Bluetooth detection error: {e}")
        return devices

    # Use asyncio to run the BLE scan
    return asyncio.run(scan_devices())
