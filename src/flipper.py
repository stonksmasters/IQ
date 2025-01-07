import serial
import subprocess
import logging
import time
import re
from utils.triangulation import rssi_to_distance, triangulate

# Configure logging for Flipper Zero
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")


def get_flipper_port():
    """
    Identify the serial port of the Flipper Zero.
    """
    try:
        result = subprocess.check_output("dmesg | grep tty", shell=True).decode()
        for line in result.splitlines():
            if "ttyACM" in line:  # Adjust for devices like /dev/ttyACM0, /dev/ttyACM1
                port_match = re.search(r"(/dev/ttyACM\d+)", line)
                if port_match:
                    return port_match.group(1)
    except Exception as e:
        logging.error(f"Error finding Flipper port: {e}")
    return None


def is_flipper_connected():
    """
    Check if Flipper Zero is connected via USB.
    """
    return get_flipper_port() is not None


def flipper_ble_scan(known_positions):
    """
    Trigger a BLE scan using the Flipper Zero via USB and parse results.
    Adds dynamic distance calculation and triangulation for devices.

    Args:
        known_positions (dict): Mapping of device addresses to known (x, y) positions.

    Returns:
        list: List of BLE devices with calculated distances and triangulated positions.
    """
    port = get_flipper_port()
    if not port:
        logging.error("Flipper Zero port not found.")
        return []

    try:
        with serial.Serial(port, 9600, timeout=5) as ser:
            ser.write(b"ble scan\r\n")  # Command to start BLE scan
            logging.info("Initiating BLE scan on Flipper Zero...")
            time.sleep(7)  # Wait for Flipper to complete scanning
            response = ser.readlines()
            devices = parse_flipper_output(response, known_positions)

            # Perform triangulation for each detected device
            triangulated_devices = []
            for device in devices:
                try:
                    if device.get("positions") and device.get("distances"):
                        device["position"] = triangulate(
                            positions=device["positions"],
                            distances=device["distances"],
                        )
                        logging.info(f"Triangulated position for {device['name']}: {device['position']}")
                        triangulated_devices.append(device)
                except Exception as e:
                    logging.error(f"Error triangulating device {device['name']}: {e}")

            logging.info(f"BLE devices found: {triangulated_devices}")
            return triangulated_devices
    except Exception as e:
        logging.error(f"Error communicating with Flipper Zero: {e}")
        return []


def parse_flipper_output(output, known_positions):
    """
    Parse the Flipper Zero BLE scan response into a structured format.

    Args:
        output (list): Raw output lines from the Flipper Zero BLE scan.
        known_positions (dict): Mapping of device addresses to known (x, y) positions.

    Returns:
        list: List of BLE devices with calculated distances and positions for triangulation.
    """
    devices = []
    for line in output:
        try:
            line_decoded = line.decode().strip()
            if "Device" in line_decoded:  # Adjust based on Flipper output format
                match = re.match(r"Device (.+) RSSI (-?\d+) dBm", line_decoded)
                if match:
                    device_address = match.group(1).strip()
                    rssi = int(match.group(2))
                    distance = rssi_to_distance(rssi)  # Calculate distance dynamically

                    device = {
                        "name": device_address,
                        "rssi": rssi,
                        "distance": distance,
                        "positions": [],
                        "distances": [],
                    }

                    # Add known positions for triangulation if available
                    if device_address in known_positions:
                        device["positions"].append(known_positions[device_address])
                        device["distances"].append(distance)

                    devices.append(device)
        except Exception as e:
            logging.warning(f"Error parsing line: {line} | Exception: {e}")
    return devices
