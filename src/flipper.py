# src/flipper.py

import serial
import subprocess
import logging
import time
import re
from utils.triangulation import triangulate

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


def flipper_ble_scan():
    """
    Trigger a BLE scan using the Flipper Zero via USB and parse results.
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
            devices = parse_flipper_output(response)

            # Perform triangulation for each detected device
            for device in devices:
                try:
                    device_positions = device.get("positions", [])
                    device_distances = device.get("distances", [])
                    if device_positions and device_distances:
                        device["position"] = triangulate(
                            positions=device_positions,
                            distances=device_distances,
                        )
                        logging.info(f"Triangulated position for {device['name']}: {device['position']}")
                except Exception as e:
                    logging.error(f"Error triangulating device {device['name']}: {e}")

            logging.info(f"BLE devices found: {devices}")
            return devices
    except Exception as e:
        logging.error(f"Error communicating with Flipper Zero: {e}")
        return []


def parse_flipper_output(output):
    """
    Parse the Flipper Zero BLE scan response into a structured format.
    """
    devices = []
    for line in output:
        try:
            line_decoded = line.decode().strip()
            if "Device" in line_decoded:  # Adjust based on Flipper output format
                match = re.match(r"Device (.+) RSSI (-?\d+) dBm", line_decoded)
                if match:
                    devices.append({
                        "name": match.group(1).strip() or "Unknown",
                        "rssi": int(match.group(2)),
                        # Placeholder for triangulation data
                        "positions": [],  # List of known positions (e.g., [(x1, y1), (x2, y2)])
                        "distances": [],  # List of distances corresponding to the positions
                    })
        except Exception as e:
            logging.warning(f"Error parsing line: {line} | Exception: {e}")
    return devices
