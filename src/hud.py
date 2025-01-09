import cv2
import os
import logging
import random

# Configure logging for hud.py
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
    handlers=[
        logging.FileHandler("hud.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Get the absolute path of the current file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Paths to the icons
WIFI_ICON_PATH = os.path.join(BASE_DIR, "../static/images/icons/wifi_icon.png")
BLUETOOTH_ICON_PATH = os.path.join(BASE_DIR, "../static/images/icons/bluetooth_icon.png")

# Normalize paths
WIFI_ICON_PATH = os.path.normpath(WIFI_ICON_PATH)
BLUETOOTH_ICON_PATH = os.path.normpath(BLUETOOTH_ICON_PATH)

def load_icon(path):
    """
    Load an icon image from the specified path.

    Args:
        path (str): Path to the icon image.

    Returns:
        numpy.ndarray or None: Loaded image or None if failed.
    """
    icon = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if icon is None:
        logger.error(f"Unable to load icon from {path}")
    return icon

# Load icons
WIFI_ICON = load_icon(WIFI_ICON_PATH)
BLUETOOTH_ICON = load_icon(BLUETOOTH_ICON_PATH)


def overlay_box(frame, position, label, color, icon=None, icon_size=(24, 24)):
    """
    Overlays a box with an optional icon and label text on the frame.

    Args:
        frame (numpy.ndarray): The video frame.
        position (tuple): (x, y) coordinates for the top-left corner of the box.
        label (str): Text label to display.
        color (tuple): BGR color for the box.
        icon (numpy.ndarray, optional): Icon image to overlay.
        icon_size (tuple, optional): Desired size for the icon.
    """
    x, y = position
    box_w, box_h = 150, 100  # Box size

    # Draw the rectangle
    cv2.rectangle(frame, (x, y), (x + box_w, y + box_h), color, 2)

    # Overlay the icon in the top-left corner of the box
    if icon is not None:
        try:
            icon_resized = cv2.resize(icon, icon_size, interpolation=cv2.INTER_AREA)
            if icon_resized.shape[2] == 4:  # Handle alpha channel
                alpha_icon = icon_resized[:, :, 3] / 255.0
                for c in range(3):
                    frame[y:y+icon_size[1], x:x+icon_size[0], c] = (
                        alpha_icon * icon_resized[:, :, c] +
                        (1 - alpha_icon) * frame[y:y+icon_size[1], x:x+icon_size[0], c]
                    )
            else:
                frame[y:y+icon_size[1], x:x+icon_size[0]] = icon_resized
        except Exception as e:
            logger.error(f"Error overlaying icon at {position}: {e}")

    # Add label text
    text_x = x + icon_size[0] + 10  # Offset text to the right of the icon
    text_y = y + 20
    font_scale = 0.6
    font_thickness = 2
    text_color = (255, 255, 255)  # White text
    cv2.putText(frame, label, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX,
                font_scale, text_color, font_thickness)


def overlay_hud(frame, signals, selected_signal, detected_objects=None):
    """
    Overlays detected Wi-Fi, Bluetooth sources, and triangulated positions on the frame,
    along with any detected objects as bounding boxes.

    Args:
        frame (numpy.ndarray): Current video frame.
        signals (list): List of combined signals (Wi-Fi, Bluetooth, and triangulated data).
        selected_signal (dict): Currently tracked signal type and name.
        detected_objects (list): List of detected objects with their bounding boxes and labels.

    Returns:
        numpy.ndarray: The frame with HUD overlays applied.
    """
    frame_height, frame_width = frame.shape[:2]

    # Define properties
    colors = {
        "wifi": (0, 255, 0),          # Green
        "bluetooth": (255, 0, 0),     # Blue
        "triangulated": (0, 255, 255),# Yellow
        "object": (0, 0, 255),        # Red
    }
    text_color = (255, 255, 255)     # White

    # Filter signals based on selection
    if selected_signal and selected_signal["type"] and selected_signal["name"]:
        filtered_signals = [
            signal for signal in signals
            if signal.get("type") == selected_signal["type"] and signal.get("name") == selected_signal["name"]
        ]
    else:
        filtered_signals = signals

    # Overlay each signal
    for signal in filtered_signals:
        position = signal.get("position", (
            random.randint(50, frame_width - 200),
            random.randint(50, frame_height - 200)
        ))
        label = f"{signal.get('name', 'Unknown')} ({signal.get('rssi', 'N/A')} dBm)"
        signal_type = signal.get("type", "unknown")
        color = colors.get(signal_type, (255, 255, 255))  # Default to white if type unknown
        icon = WIFI_ICON if signal_type == "wifi" else BLUETOOTH_ICON if signal_type == "bluetooth" else None
        overlay_box(frame, position, label, color, icon)

    # Overlay detected objects
    if detected_objects:
        for obj in detected_objects:
            bbox = obj.get("bbox", (0, 0, 0, 0))
            label = obj.get("label", "Object")
            x, y, w, h = bbox

            # Draw the bounding box
            cv2.rectangle(frame, (x, y), (x + w, y + h), colors["object"], 2)

            # Add label text above the box
            text_x, text_y = x, y - 10
            cv2.putText(frame, label, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, text_color, 2)

    return frame
