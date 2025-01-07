import subprocess
from bleak import BleakScanner
import asyncio
import logging
import math
from typing import List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")

def detect_wifi() -> List[Dict[str, any]]:
    """
    Scans for nearby Wi-Fi networks and returns a list of dictionaries
    containing SSID, signal strength, and estimated distances.
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
                raw_signal = signal_line[0].split("=")[1].strip()

                # Parse signal strength
                if '/' in raw_signal:
                    signal = raw_signal.split('/')[0]  # Take the first part before '/'
                else:
                    signal = raw_signal.split(" ")[0]
                try:
                    signal = int(signal)
                except ValueError:
                    logging.warning(f"Non-integer signal strength '{raw_signal}' for SSID '{ssid}'")
                    signal = 0

                # Estimate distance (simple model, can be replaced with a more accurate one)
                distance = calculate_wifi_distance(signal)

                networks.append({"SSID": ssid, "signal": signal, "distance": distance})
    except Exception as e:
        logging.error(f"Wi-Fi detection error: {e}")
    return networks

def detect_bluetooth() -> List[Dict[str, any]]:
    """
    Scans for Bluetooth Low Energy (BLE) devices and returns a list of found devices
    with their name, address, RSSI, and estimated distances.
    """
    async def scan_devices():
        devices = []

        def detection_callback(device, advertisement_data):
            rssi = advertisement_data.rssi
            distance = calculate_bluetooth_distance(rssi)
            devices.append({
                "name": device.name or "Unknown",
                "address": device.address,
                "rssi": rssi,
                "distance": distance
            })

        try:
            scanner = BleakScanner(detection_callback=detection_callback)
            await scanner.start()
            await asyncio.sleep(5)  # Scan for 5 seconds
            await scanner.stop()
        except Exception as e:
            logging.error(f"Bluetooth detection error: {e}")

        return devices

    # Use asyncio to run the BLE scan
    return asyncio.run(scan_devices())

def calculate_wifi_distance(signal: int) -> float:
    """
    Estimate the distance to a Wi-Fi signal based on its RSSI using a simplified path loss model.
    """
    # Constants for the path loss model
    A = -50  # RSSI at 1 meter
    n = 2  # Path loss exponent (typical indoor value)

    try:
        distance = 10 ** ((A - signal) / (10 * n))
    except Exception as e:
        logging.warning(f"Error calculating Wi-Fi distance: {e}")
        distance = float('inf')  # Return infinity if calculation fails

    return round(distance, 2)

def calculate_bluetooth_distance(rssi: int) -> float:
    """
    Estimate the distance to a Bluetooth signal based on its RSSI using a simplified path loss model.
    """
    # Constants for the path loss model
    A = -59  # RSSI at 1 meter
    n = 2  # Path loss exponent (typical indoor value)

    try:
        distance = 10 ** ((A - rssi) / (10 * n))
    except Exception as e:
        logging.warning(f"Error calculating Bluetooth distance: {e}")
        distance = float('inf')  # Return infinity if calculation fails

    return round(distance, 2)

def prepare_triangulation_data(wifi_results, bluetooth_results, known_positions):
    """
    Prepares Wi-Fi and Bluetooth data for triangulation by mapping devices to known positions.

    Args:
        wifi_results (list): Detected Wi-Fi networks with distances.
        bluetooth_results (list): Detected Bluetooth devices with distances.
        known_positions (dict): Mapping of device addresses/SSIDs to known (x, y) positions.

    Returns:
        dict: Contains lists of triangulation-ready Wi-Fi and Bluetooth devices.
    """
    wifi_triangulation = []
    bluetooth_triangulation = []

    for wifi in wifi_results:
        ssid = wifi.get("SSID")
        if ssid in known_positions and wifi.get("distance") is not None:
            wifi_triangulation.append({
                "position": known_positions[ssid],
                "distance": wifi["distance"],
                "name": ssid,
            })

    for bluetooth in bluetooth_results:
        address = bluetooth.get("address")
        if address in known_positions and bluetooth.get("distance") is not None:
            bluetooth_triangulation.append({
                "position": known_positions[address],
                "distance": bluetooth["distance"],
                "name": bluetooth.get("name"),
            })

    return {
        "wifi": wifi_triangulation,
        "bluetooth": bluetooth_triangulation,
    }

if __name__ == "__main__":
    # Example known positions (e.g., Raspberry Pi, Flipper Zero)
    known_positions = {
        "RaspberryPi": (0, 0),  # Example position for a Wi-Fi device
        "FlipperZero": (5, 5),  # Example position for a Bluetooth device
    }

    # Test Wi-Fi detection
    logging.info("Scanning for Wi-Fi networks...")
    wifi_results = detect_wifi()
    for wifi in wifi_results:
        logging.info(f"Wi-Fi: {wifi}")

    # Test Bluetooth detection
    logging.info("Scanning for Bluetooth devices...")
    bluetooth_results = detect_bluetooth()
    for bluetooth in bluetooth_results:
        logging.info(f"Bluetooth: {bluetooth}")

    # Prepare data for triangulation
    triangulation_data = prepare_triangulation_data(wifi_results, bluetooth_results, known_positions)
    logging.info(f"Triangulation Data: {triangulation_data}")
