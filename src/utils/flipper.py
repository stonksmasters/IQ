# src/flipper.py

import serial
import subprocess
import logging
import time

# Configure logging for Flipper Zero
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")

def get_flipper_port():
    """
    Identify the serial port of the Flipper Zero.
    """
    try:
        result = subprocess.check_output("dmesg | grep tty", shell=True).decode()
        for line in result.splitlines():
            if "ttyACM0" in line:
                return "/dev/ttyACM0"
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
        with serial.Serial(port, 9600, timeout=2) as ser:
            ser.write(b"ble scan\r\n")  # Command to start BLE scan
            time.sleep(5)  # Wait for Flipper to complete scanning
            response = ser.readlines()
            return parse_flipper_output(response)
    except Exception as e:
        logging.error(f"Error communicating with Flipper Zero: {e}")
        return []

def parse_flipper_output(output):
    """
    Parse the Flipper Zero BLE scan response into a structured format.
    """
    devices = []
    for line in output:
        line_decoded = line.decode().strip()
        if "Device" in line_decoded:  # Adjust based on Flipper output format
            parts = line_decoded.split()
            devices.append({
                "name": parts[1],
                "rssi": int(parts[-1].replace("dBm", "")),
            })
    return devices
