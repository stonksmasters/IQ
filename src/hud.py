# src/hud.py

import cv2
import os
import logging

# Configure logging for hud.py
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

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


def overlay_hud(frame, wifi_signals, bluetooth_signals, flipper_signals):
    """
    Overlays Wi-Fi and Bluetooth signals on the video frame with enhanced visuals.
    """
    # Define HUD display properties
    x_start = 10
    y_start = 30
    line_height = 30
    icon_size = 24  # Resize icons to a consistent size
    alpha = 0.6  # Transparency for background

    # Overlay a semi-transparent background
    overlay = frame.copy()
    cv2.rectangle(overlay, (5, 5), (350, 250), (0, 0, 0), -1)
    frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

    # Function to add icon and text
    def add_hud_item(icon, text, position):
        try:
            # Resize icon
            if icon is not None:
                icon_resized = cv2.resize(icon, (icon_size, icon_size), interpolation=cv2.INTER_AREA)
                roi = frame[position[1]:position[1] + icon_size, position[0]:position[0] + icon_size]
                if icon_resized.shape[2] == 4:  # Handle alpha channel
                    alpha_icon = icon_resized[:, :, 3] / 255.0
                    for c in range(3):
                        roi[:, :, c] = (alpha_icon * icon_resized[:, :, c] + (1 - alpha_icon) * roi[:, :, c])
                else:
                    roi[:] = icon_resized
        except Exception as e:
            logging.error(f"Error overlaying icon at {position}: {e}")

        # Add text
        cv2.putText(frame, text, (position[0] + icon_size + 10, position[1] + icon_size - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    # Overlay Wi-Fi signals
    y_offset = y_start
    if wifi_signals:
        logging.info(f"Overlaying {len(wifi_signals)} Wi-Fi networks.")
        for network in sorted(wifi_signals, key=lambda x: int(x.get('signal', -100)), reverse=True):
            text = f"{network['SSID']} ({network['signal']} dBm)"
            add_hud_item(WIFI_ICON, text, (x_start, y_offset))
            y_offset += line_height

    # Overlay Bluetooth signals
    y_offset += 20  # Add some spacing between Wi-Fi and Bluetooth sections
    if bluetooth_signals:
        logging.info(f"Overlaying {len(bluetooth_signals)} Bluetooth devices.")
        for device in sorted(bluetooth_signals, key=lambda x: int(x.get('rssi', -100)), reverse=True):
            text = f"{device['name']} ({device['rssi']} dBm)"
            add_hud_item(BLUETOOTH_ICON, text, (x_start, y_offset))
            y_offset += line_height

    return frame
