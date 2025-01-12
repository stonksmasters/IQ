#/src/hud.py


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
ICON_DIR = os.path.join(BASE_DIR, "../src/static/images/icons")
WIFI_ICON_PATH = os.path.join(ICON_DIR, "wifi_icon.png")
BLUETOOTH_ICON_PATH = os.path.join(ICON_DIR, "bluetooth_icon.png")
FLIPPER_ICON_PATH = os.path.join(ICON_DIR, "flipper_icon.png")  # Add a Flipper icon

# Normalize paths
WIFI_ICON_PATH = os.path.normpath(WIFI_ICON_PATH)
BLUETOOTH_ICON_PATH = os.path.normpath(BLUETOOTH_ICON_PATH)
FLIPPER_ICON_PATH = os.path.normpath(FLIPPER_ICON_PATH)

def load_icon(path):
    """
    Load an icon image from the specified path.

    Args:
        path (str): Path to the icon image.

    Returns:
        numpy.ndarray or None: Loaded image or None if it fails.
    """
    icon = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if icon is None:
        logger.error(f"Unable to load icon from {path}")
    return icon

# Load icons
WIFI_ICON = load_icon(WIFI_ICON_PATH)
BLUETOOTH_ICON = load_icon(BLUETOOTH_ICON_PATH)
FLIPPER_ICON = load_icon(FLIPPER_ICON_PATH)

def overlay_box(frame, position, label, color, icon=None, icon_size=(24, 24)):
    """
    Overlays a rectangular box with an optional icon and label text on the frame.

    Args:
        frame (numpy.ndarray): The video frame.
        position (tuple): (x, y) coordinates for the top-left corner of the box.
        label (str): Text label to display.
        color (tuple): BGR color for the box border.
        icon (numpy.ndarray, optional): Icon image to overlay.
        icon_size (tuple, optional): Desired size for the icon.
    """
    x, y = position
    box_w, box_h = 150, 50  # Box size

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
    text_x = x + icon_size[0] + 10
    text_y = y + 30
    font_scale = 0.6
    font_thickness = 2
    text_color = (255, 255, 255)
    cv2.putText(
        frame, label, (text_x, text_y),
        cv2.FONT_HERSHEY_SIMPLEX, font_scale,
        text_color, font_thickness
    )

def overlay_hud(frame, signals, selected_signal, detected_objects=None):
    """
    Overlays detected Wi-Fi, Bluetooth, and Flipper signals on the frame.

    Args:
        frame (numpy.ndarray): Current video frame.
        signals (list): List of combined signals (Wi-Fi, Bluetooth, Flipper, etc.).
        selected_signal (dict): The tracked signal's data with "type", "name", and optional "position".
        detected_objects (list): List of detected objects (each with "bbox" and "label").

    Returns:
        numpy.ndarray: The frame with HUD overlays applied.
    """
    frame_height, frame_width = frame.shape[:2]

    # Define color properties
    colors = {
        "wifi": (0, 255, 0),       # Green for Wi-Fi
        "bluetooth": (255, 0, 0),  # Blue for Bluetooth
        "flipper": (0, 255, 255),  # Yellow for Flipper
        "object": (0, 0, 255)      # Red for detected objects
    }
    tracked_color = (0, 0, 255)    # Red for the tracked signal
    text_color = (255, 255, 255)   # White text

    # Filter and highlight tracked signals
    tracked_type = selected_signal.get("type")
    tracked_name = selected_signal.get("name")
    filtered_signals = signals

    # Filter signals based on the tracked type and name
    if tracked_type and tracked_name:
        filtered_signals = [
            sig for sig in signals
            if sig.get("type") == tracked_type and sig.get("name") == tracked_name
        ]
        # Add a fallback signal if none match
        if not filtered_signals:
            fallback_signal = {
                "type": tracked_type,
                "name": tracked_name,
                "rssi": "N/A",
                "position": selected_signal.get("position") or (
                    random.randint(50, frame_width - 200),
                    random.randint(50, frame_height - 200)
                )
            }
            filtered_signals.append(fallback_signal)

    # Overlay signals
    for signal in filtered_signals:
        position = signal.get("position", (
            random.randint(50, frame_width - 200),
            random.randint(50, frame_height - 200)
        ))
        label = f"{signal.get('name', 'Unknown')} ({signal.get('rssi', 'N/A')} dBm)"
        color = colors.get(signal.get("type"), (255, 255, 255))
        icon = WIFI_ICON if signal.get("type") == "wifi" else BLUETOOTH_ICON if signal.get("type") == "bluetooth" else FLIPPER_ICON
        overlay_box(frame, position, label, color, icon)

    # Highlight the tracked signal position
    if selected_signal.get("position"):
        x, y = selected_signal["position"]
        cv2.rectangle(frame, (x, y), (x + 50, y + 50), tracked_color, 2)
        cv2.putText(frame, "Tracking", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, tracked_color, 2)

    # Overlay detected objects
    if detected_objects:
        for obj in detected_objects:
            bbox = obj.get("bbox", (0, 0, 0, 0))  # (x, y, w, h)
            label = obj.get("label", "Object")
            x, y, w, h = bbox
            cv2.rectangle(frame, (x, y), (x + w, y + h), colors["object"], 2)
            cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)

    return frame
