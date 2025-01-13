# src/flipper.py

import serial
import serial.tools.list_ports
import logging
import time
import re
import threading

from shared import signals_data, signals_lock
from config import config

def find_flipper_zero():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "Flipper" in port.description or "ttyACM" in port.device:
            logging.info(f"Flipper Zero found on port: {port.device}")
            return port.device
    logging.warning("No Flipper Zero device found.")
    return None

def is_flipper_connected():
    return find_flipper_zero() is not None

def ble_scan_with_flipper(port):
    """Example BLE scan logic with Flipper Zero; update signals_data accordingly."""
    try:
        with serial.Serial(port, 115200, timeout=5) as ser:
            logging.info("Flipper Zero is connected.")
            # Example: send BLE scan command (pseudo-code)
            # ser.write(b"scan_ble\r\n")
            # read lines, parse output
            # example -> signals_data["bluetooth"].append(...)
            pass
    except serial.SerialException as e:
        logging.error(f"Serial exception: {e}")

def background_flipper_scanner():
    """Continuously attempt BLE scans with Flipper Zero."""
    while True:
        port = find_flipper_zero()
        if port:
            ble_scan_with_flipper(port)
        else:
            logging.warning("Flipper Zero not connected. Attempting to reconnect...")

        time.sleep(10)

def init_flipper_zero():
    t = threading.Thread(target=background_flipper_scanner, daemon=True)
    t.start()

# Initialize on import
init_flipper_zero()
