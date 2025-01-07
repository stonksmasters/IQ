import numpy as np

def triangulate(positions, distances):
    """
    Compute the 2D position of a signal source using multilateration.

    Args:
        positions (list of tuples): Known positions of scanning devices [(x1, y1), (x2, y2), ...].
        distances (list of floats): Distances from each scanning device to the signal source.

    Returns:
        tuple: Estimated (x, y) position of the signal source.
    """
    # Ensure we have at least 3 devices
    if len(positions) < 3 or len(distances) < 3:
        raise ValueError("At least 3 scanning devices are required for triangulation.")

    A = []
    b = []

    for i in range(1, len(positions)):
        x1, y1 = positions[0]
        x2, y2 = positions[i]
        d1 = distances[0]
        d2 = distances[i]

        A.append([2 * (x2 - x1), 2 * (y2 - y1)])
        b.append(d1**2 - d2**2 - x1**2 - y1**2 + x2**2 + y2**2)

    A = np.array(A)
    b = np.array(b).reshape(-1, 1)

    try:
        # Solve the linear system Ax = b
        result = np.linalg.lstsq(A, b, rcond=None)[0]
        return result[0][0], result[1][0]  # Estimated (x, y) position
    except Exception as e:
        raise RuntimeError(f"Error in triangulation: {e}")
