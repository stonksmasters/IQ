import cv2
import os
import logging
import random

# Configure logging for hud.py
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")

# Get the absolute path of the current file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Paths to the icons
WIFI_ICON_PATH = os.path.join(BASE_DIR, "../src/static/images/icons/wifi_icon.png")
BLUETOOTH_ICON_PATH = os.path.join(BASE_DIR, "../src/static/images/icons/bluetooth_icon.png")

# Normalize paths
WIFI_ICON_PATH = os.path.normpath(WIFI_ICON_PATH)
BLUETOOTH_ICON_PATH = os.path.normpath(BLUETOOTH_ICON_PATH)

# Load icons using absolute paths
WIFI_ICON = cv2.imread(WIFI_ICON_PATH, cv2.IMREAD_UNCHANGED)
BLUETOOTH_ICON = cv2.imread(BLUETOOTH_ICON_PATH, cv2.IMREAD_UNCHANGED)

if WIFI_ICON is None:
    logging.error(f"Unable to load Wi-Fi icon from {WIFI_ICON_PATH}")
if BLUETOOTH_ICON is None:
    logging.error(f"Unable to load Bluetooth icon from {BLUETOOTH_ICON_PATH}")

def overlay_hud(frame, signals, selected_signal, detected_objects=None):
    """
    Overlays detected Wi-Fi, Bluetooth sources, and triangulated positions on the frame,
    along with any detected objects as bounding boxes.

    Args:
        frame (numpy.ndarray): Current video frame.
        signals (list): List of combined signals (Wi-Fi, Bluetooth, and triangulated data).
        selected_signal (dict): Currently tracked signal type and name.
        detected_objects (list): List of detected objects with their bounding boxes and labels.
    """
    frame_height, frame_width = frame.shape[:2]

    # Define properties
    font_scale = 0.6
    font_thickness = 2
    wifi_color = (0, 255, 0)  # Green for Wi-Fi sources
    bluetooth_color = (255, 0, 0)  # Blue for Bluetooth sources
    triangulated_color = (0, 255, 255)  # Yellow for triangulated positions
    object_color = (0, 0, 255)  # Red for detected objects
    text_color = (255, 255, 255)  # White text

    def overlay_box(position, label, color, icon=None):
        """
        Overlays a box with optional icon and label text.
        """
        x, y = position
        box_w, box_h = 150, 100  # Box size

        # Draw the rectangle
        cv2.rectangle(frame, (x, y), (x + box_w, y + box_h), color, 2)

        # Overlay the icon in the top-left corner of the box
        if icon is not None:
            try:
                icon_resized = cv2.resize(icon, (24, 24), interpolation=cv2.INTER_AREA)
                if icon_resized.shape[2] == 4:  # Handle alpha channel
                    alpha_icon = icon_resized[:, :, 3] / 255.0
                    for c in range(3):
                        frame[y:y+24, x:x+24, c] = (
                            alpha_icon * icon_resized[:, :, c] +
                            (1 - alpha_icon) * frame[y:y+24, x:x+24, c]
                        )
                else:
                    frame[y:y+24, x:x+24] = icon_resized
            except Exception as e:
                logging.error(f"Error overlaying icon at {position}: {e}")

        # Add label text
        text_x = x + 30
        text_y = y + 20
        cv2.putText(frame, label, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale, text_color, font_thickness)

    # Filter for the selected signal
    filtered_signals = []
    if selected_signal and selected_signal["type"] and selected_signal["name"]:
        filtered_signals = [
            signal for signal in signals
            if signal.get("type") == selected_signal["type"] and signal.get("name") == selected_signal["name"]
        ]
    else:
        filtered_signals = signals

    # Overlay signals
    for signal in filtered_signals:
        position = signal.get("position", (random.randint(50, frame_width - 200),
                                           random.randint(50, frame_height - 200)))
        label = f"{signal.get('name', 'Unknown')} ({signal.get('rssi', 'N/A')} dBm)"
        color = triangulated_color if "position" in signal else bluetooth_color
        icon = WIFI_ICON if signal.get("type") == "wifi" else BLUETOOTH_ICON
        overlay_box(position, label, color, icon)

    # Overlay detected objects
    if detected_objects:
        for obj in detected_objects:
            bbox = obj["bbox"]  # Bounding box (x, y, w, h)
            label = obj["label"]
            x, y, w, h = bbox

            # Draw the bounding box
            cv2.rectangle(frame, (x, y), (x + w, y + h), object_color, 2)

            # Add label text above the box
            text_x, text_y = x, y - 10
            cv2.putText(frame, label, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX,
                        font_scale, text_color, font_thickness)

    return frame
