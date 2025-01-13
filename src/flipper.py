# src/flipper.py

import serial
import serial.tools.list_ports
import logging
import time
import re
from utils.triangulation import rssi_to_distance, triangulate
from shared import signals_data, signals_lock, selected_signal
from config import config
import threading  # Ensure threading is imported

def find_flipper_zero():
    """Find the Flipper Zero device connected via serial."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "Flipper" in port.description:
            logging.info(f"Flipper Zero found on port: {port.device}")
            return port.device
    logging.warning("No Flipper Zero device found.")
    return None

def background_flipper_scanner():
    """Background thread to scan for BLE devices using Flipper Zero."""
    while True:
        flipper_port = find_flipper_zero()
        if flipper_port:
            try:
                ser = serial.Serial(flipper_port, 115200, timeout=1)
                logging.info("Flipper Zero is connected.")
                # Implement BLE scanning logic here
                # Example:
                # ser.write(b'scan_ble\n')
                # response = ser.readline()
                # Parse response and update signals_data
                ser.close()
            except serial.SerialException as e:
                logging.error(f"Serial exception: {e}")
        else:
            logging.warning("Flipper Zero not connected. Attempting to reconnect...")

        time.sleep(10)  # Wait before next scan attempt

# Initialize and start the Flipper Zero scanner thread
def init_flipper_zero():
    scanner_thread = threading.Thread(target=background_flipper_scanner, daemon=True)
    scanner_thread.start()

# Call initialization function on module import
init_flipper_zero()

def fetch_flipper_data():
    """Function to fetch data from Flipper Zero."""
    # Implement data fetching logic here
    pass
