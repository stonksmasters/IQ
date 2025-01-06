import subprocess
import bluetooth

def detect_wifi():
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
    devices = []
    try:
        nearby_devices = bluetooth.discover_devices(duration=8, lookup_names=True, lookup_class=True)
        for addr, name, device_class in nearby_devices:
            # Placeholder for RSSI; PyBluez doesn't provide RSSI directly
            rssi = "N/A"
            devices.append((name, addr, rssi))
    except Exception as e:
        print(f"Bluetooth detection error: {e}")
    return devices
