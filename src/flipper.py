import serial
import serial.tools.list_ports
import logging
import time
import re
from utils.triangulation import rssi_to_distance, triangulate

# Configure logging for Flipper Zero
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
    handlers=[
        logging.FileHandler("flipper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Default VID:PID for Flipper Zero (update this as needed)
DEFAULT_VID_PID = "0483:5740"  # Flipper Zero's VID:PID

def get_flipper_port():
    """
    Identify the serial port of the Flipper Zero by matching VID and PID.

    Returns:
        str or None: Serial port path if found, else None.
    """
    try:
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if DEFAULT_VID_PID in port.hwid:
                logger.info(f"Flipper Zero found on port: {port.device}")
                return port.device
        logger.warning("No Flipper Zero device found.")
    except Exception as e:
        logger.error(f"Error finding Flipper port: {e}")
    return None


def is_flipper_connected():
    """
    Check if Flipper Zero is connected via USB.

    Returns:
        bool: True if connected, False otherwise.
    """
    port = get_flipper_port()
    if port:
        logger.info("Flipper Zero is connected.")
        return True
    else:
        logger.info("Flipper Zero is not connected.")
        return False


def flipper_ble_scan(known_positions):
    """
    Trigger a BLE scan using the Flipper Zero via USB and parse results.

    Args:
        known_positions (dict): Mapping of device addresses to known (x, y) positions.

    Returns:
        list: List of BLE devices with calculated distances and triangulated positions.
    """
    port = get_flipper_port()
    if not port:
        logger.error("Flipper Zero port not found.")
        return []

    try:
        with serial.Serial(port, 9600, timeout=5) as ser:
            ser.reset_input_buffer()
            ser.write(b"ble scan\r\n")  # Command to start BLE scan
            logger.info("Initiating BLE scan on Flipper Zero...")
            time.sleep(7)  # Adjust time based on your environment
            response = ser.read_all().decode(errors='ignore')
            logger.debug(f"Raw BLE scan response: {response}")
            devices = parse_flipper_output(response, known_positions)

            # Perform triangulation for each detected device
            triangulated_devices = []
            for device in devices:
                if device.get("positions") and device.get("distances"):
                    try:
                        device["position"] = triangulate(
                            positions=device["positions"],
                            distances=device["distances"]
                        )
                        logger.info(f"Triangulated position for {device['name']}: {device['position']}")
                        triangulated_devices.append(device)
                    except Exception as e:
                        logger.error(f"Error triangulating device {device['name']}: {e}")

            logger.info(f"BLE devices found: {triangulated_devices}")
            return triangulated_devices
    except serial.SerialException as e:
        logger.error(f"Serial communication error with Flipper Zero: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during BLE scan: {e}")
    return []


def parse_flipper_output(output, known_positions):
    """
    Parse the Flipper Zero BLE scan response into a structured format.

    Args:
        output (str): Raw output string from the Flipper Zero BLE scan.
        known_positions (dict): Mapping of device addresses to known (x, y) positions.

    Returns:
        list: List of BLE devices with calculated distances and positions for triangulation.
    """
    devices = []
    for line in output.splitlines():
        try:
            if "Device" in line:
                match = re.match(r"Device\s+([0-9A-Fa-f:]+)\s+RSSI\s+(-?\d+)\s+dBm", line)
                if match:
                    device_address = match.group(1).strip()
                    rssi = int(match.group(2))
                    distance = rssi_to_distance(rssi)

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
            logger.warning(f"Error parsing line: '{line}' | Exception: {e}")
    return devices


def fetch_flipper_data(known_positions={}):
    """
    Fetch data from Flipper Zero via BLE scan.

    Args:
        known_positions (dict): Mapping of known device addresses to positions.

    Returns:
        list: List of scanned devices with calculated distances and positions.
    """
    return flipper_ble_scan(known_positions)
