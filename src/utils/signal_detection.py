import subprocess
from bleak import BleakScanner
import asyncio
import logging
import math
from typing import List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")
logger = logging.getLogger(__name__)

# Configurable constants
WIFI_SCAN_INTERFACE = "wlan0"  # Default Wi-Fi interface
WIFI_SCAN_DURATION = 5  # Duration for BLE scanning
PATH_LOSS_CONSTANTS = {
    "wifi": {"A": -50, "n": 2},  # RSSI at 1 meter, Path loss exponent for Wi-Fi
    "bluetooth": {"A": -59, "n": 2},  # RSSI at 1 meter, Path loss exponent for Bluetooth
}

def detect_wifi() -> List[Dict[str, any]]:
    """
    Scans for nearby Wi-Fi networks and returns a list of dictionaries
    containing SSID, signal strength, and estimated distances.
    """
    networks = []
    try:
        result = subprocess.run(["iwlist", WIFI_SCAN_INTERFACE, "scan"], capture_output=True, text=True)
        output = result.stdout
        cells = output.split("Cell")
        for cell in cells[1:]:
            ssid_line = [line for line in cell.split("\n") if "ESSID" in line]
            signal_line = [line for line in cell.split("\n") if "Signal level" in line]
            if ssid_line and signal_line:
                ssid = ssid_line[0].split(":")[1].strip().strip('"')
                raw_signal = signal_line[0].split("=")[1].strip()

                # Parse signal strength
                try:
                    signal = int(raw_signal.split("/")[0] if '/' in raw_signal else raw_signal.split()[0])
                except ValueError:
                    logger.warning(f"Non-integer signal strength '{raw_signal}' for SSID '{ssid}'")
                    signal = 0

                # Estimate distance
                distance = calculate_distance(signal, PATH_LOSS_CONSTANTS["wifi"])

                networks.append({"SSID": ssid, "signal": signal, "distance": distance})
    except Exception as e:
        logger.error(f"Wi-Fi detection error: {e}")
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
            distance = calculate_distance(rssi, PATH_LOSS_CONSTANTS["bluetooth"])
            devices.append({
                "name": device.name or "Unknown",
                "address": device.address,
                "rssi": rssi,
                "distance": distance
            })

        try:
            scanner = BleakScanner(detection_callback=detection_callback)
            await scanner.start()
            await asyncio.sleep(WIFI_SCAN_DURATION)  # Scan duration
            await scanner.stop()
        except Exception as e:
            logger.error(f"Bluetooth detection error: {e}")

        return devices

    return asyncio.run(scan_devices())

def calculate_distance(signal: int, constants: Dict[str, int]) -> float:
    """
    Estimate the distance to a signal source based on its RSSI using a simplified path loss model.

    Args:
        signal (int): Received Signal Strength Indicator (RSSI).
        constants (dict): Path loss model constants (e.g., "A" and "n").

    Returns:
        float: Estimated distance in meters.
    """
    try:
        A = constants["A"]
        n = constants["n"]
        distance = 10 ** ((A - signal) / (10 * n))
        return round(distance, 2)
    except Exception as e:
        logger.warning(f"Error calculating distance: {e}")
        return float('inf')  # Return infinity if calculation fails

def prepare_triangulation_data(wifi_results, bluetooth_results, known_positions):
    """
    Prepares Wi-Fi and Bluetooth data for triangulation by mapping devices to known positions.

    Args:
        wifi_results (list): Detected Wi-Fi networks with distances.
        bluetooth_results (list): Detected Bluetooth devices with distances.
        known_positions (dict): Mapping of device addresses/SSIDs to positions.

    Returns:
        dict: Contains triangulation-ready Wi-Fi and Bluetooth devices.
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
    known_positions = {
        "RaspberryPi": (0, 0),
        "FlipperZero": (5, 5),
    }

    # Test Wi-Fi detection
    logger.info("Scanning for Wi-Fi networks...")
    wifi_results = detect_wifi()
    for wifi in wifi_results:
        logger.info(f"Wi-Fi: {wifi}")

    # Test Bluetooth detection
    logger.info("Scanning for Bluetooth devices...")
    bluetooth_results = detect_bluetooth()
    for bluetooth in bluetooth_results:
        logger.info(f"Bluetooth: {bluetooth}")

    # Prepare triangulation data
    triangulation_data = prepare_triangulation_data(wifi_results, bluetooth_results, known_positions)
    logger.info(f"Triangulation Data: {triangulation_data}")
