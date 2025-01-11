import numpy as np
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")
logger = logging.getLogger(__name__)

def rssi_to_distance(rssi, A=-40, n=2):
    """
    Converts RSSI to distance using a propagation model.

    Args:
        rssi (int): Signal strength in dBm.
        A (int): RSSI at 1 meter.
        n (int): Path-loss exponent.

    Returns:
        float: Estimated distance in meters.
    """
    try:
        distance = 10 ** ((A - rssi) / (10 * n))
        return round(distance, 2)
    except Exception as e:
        logger.error(f"Error in RSSI to distance calculation: {e}")
        return None

def triangulate(positions, distances):
    """
    Compute the 2D position of a signal source using multilateration.

    Args:
        positions (list of tuples): Known positions of scanning devices [(x1, y1), (x2, y2), ...].
        distances (list of floats): Distances from each scanning device to the signal source.

    Returns:
        tuple: Estimated (x, y) position of the signal source, or None if an error occurs.
    """
    if len(positions) < 3 or len(distances) < 3:
        logger.error("At least 3 scanning devices are required for triangulation.")
        return None

    A = []
    b = []

    try:
        for i in range(1, len(positions)):
            x1, y1 = positions[0]
            x2, y2 = positions[i]
            d1 = distances[0]
            d2 = distances[i]

            A.append([2 * (x2 - x1), 2 * (y2 - y1)])
            b.append(d1**2 - d2**2 - x1**2 - y1**2 + x2**2 + y2**2)

        A = np.array(A)
        b = np.array(b).reshape(-1, 1)

        # Solve the linear system Ax = b
        result = np.linalg.lstsq(A, b, rcond=None)[0]
        return result[0][0], result[1][0]  # Estimated (x, y) position
    except Exception as e:
        logger.error(f"Error in triangulation: {e}")
        return None

def calculate_distances_and_triangulate(devices):
    """
    Calculate distances dynamically from RSSI and perform triangulation.

    Args:
        devices (list of dicts): List of device data with positions and RSSI values.
            Example:
            [
                {"position": (x1, y1), "rssi": -50},
                {"position": (x2, y2), "rssi": -60},
                {"position": (x3, y3), "rssi": -70},
            ]

    Returns:
        tuple: Estimated (x, y) position of the signal source, or None if triangulation fails.
    """
    positions = []
    distances = []

    for device in devices:
        position = device.get("position")
        rssi = device.get("rssi")
        A = device.get("A", -40)  # Allow custom RSSI at 1 meter
        n = device.get("n", 2)    # Allow custom path-loss exponent

        if position and rssi is not None:
            distance = rssi_to_distance(rssi, A=A, n=n)
            if distance is not None:
                positions.append(position)
                distances.append(distance)
            else:
                logger.warning(f"Invalid distance calculated for device at position {position} with RSSI {rssi}.")
        else:
            logger.warning(f"Missing position or RSSI for device: {device}")

    if len(positions) >= 3:
        return triangulate(positions, distances)
    else:
        logger.error("Insufficient data for triangulation. At least 3 devices are required.")
        return None

if __name__ == "__main__":
    # Example usage
    devices = [
        {"position": (0, 0), "rssi": -50},
        {"position": (5, 0), "rssi": -60},
        {"position": (0, 5), "rssi": -70},
        # Custom model parameters for one device
        {"position": (3, 3), "rssi": -65, "A": -45, "n": 2.5},
    ]

    estimated_position = calculate_distances_and_triangulate(devices)
    if estimated_position:
        logger.info(f"Estimated position of the signal source: {estimated_position}")
    else:
        logger.error("Failed to estimate position.")
