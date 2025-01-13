# src/flipper.py

import serial
import serial.tools.list_ports
import logging
import time
import re
import threading

from shared import signals_data, signals_lock

# Optional: If your code references config or other modules, import them here as needed
# from config import config

def find_flipper_zero():
    """Locate the Flipper Zero port if connected."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "Flipper" in port.description or "ttyACM" in port.device:
            logging.info(f"Flipper Zero found on port: {port.device}")
            return port.device
    logging.warning("No Flipper Zero device found.")
    return None

def is_flipper_connected():
    """Check if Flipper Zero is connected."""
    return find_flipper_zero() is not None

def background_flipper_scanner():
    """
    Continuously scan or perform tasks with Flipper Zero in a background thread.
    (Optional: Add your BLE scanning, etc., inside here.)
    """
    while True:
        port = find_flipper_zero()
        if port:
            # Example logic: read data or do something
            logging.info("Flipper Zero is connected.")
            # ...
        else:
            logging.warning("Flipper Zero not connected. Attempting to reconnect...")

        time.sleep(10)

def init_flipper_zero():
    """
    Initialize the Flipper Zero background scanner thread.
    """
    t = threading.Thread(target=background_flipper_scanner, daemon=True)
    t.start()

# ------------------------------------------------------------------------
# The critical fix: Define the `fetch_flipper_data` function.
# ------------------------------------------------------------------------
def fetch_flipper_data():
    """
    This function must exist so that 'from flipper import fetch_flipper_data'
    doesn't fail. Adjust its logic as needed to return or update signals_data.
    """
    # Stub logic: either return data, or update signals_data
    logging.info("fetch_flipper_data() called — implement your logic here.")
    return []

# Optionally call init_flipper_zero() automatically upon import
init_flipper_zero()
