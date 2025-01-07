# src/hud.py

import cv2
import os
import logging
import random  # For simulated source positions

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
    Overlays detected Wi-Fi and Bluetooth sources as boxes with icons and information.
    """
    frame_height, frame_width = frame.shape[:2]

    # Define properties
    font_scale = 0.6
    font_thickness = 2
    wifi_color = (0, 255, 0)  # Green for Wi-Fi sources
    bluetooth_color = (255, 0, 0)  # Blue for Bluetooth sources
    text_color = (255, 255, 255)  # White text

    # Function to overlay a box, icon, and text
    def overlay_source(position, icon, label, color):
        x, y = position
        box_w, box_h = 150, 100  # Box size

        # Draw a rectangle for the source
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

        # Add label text below the icon
        text_x = x + 30
        text_y = y + 20
        cv2.putText(frame, label, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale, text_color, font_thickness)

    # Process Wi-Fi signals
    if wifi_signals:
        logging.info(f"Overlaying {len(wifi_signals)} Wi-Fi networks.")
        for network in wifi_signals:
            # Simulate source position (replace with actual detection logic)
            x = random.randint(50, frame_width - 200)
            y = random.randint(50, frame_height - 200)

            # Prepare label with SSID and signal strength
            label = f"{network['SSID']} ({network['signal']} dBm)"
            overlay_source((x, y), WIFI_ICON, label, wifi_color)

    # Process Bluetooth signals
    if bluetooth_signals:
        logging.info(f"Overlaying {len(bluetooth_signals)} Bluetooth devices.")
        for device in bluetooth_signals:
            # Simulate source position (replace with actual detection logic)
            x = random.randint(50, frame_width - 200)
            y = random.randint(50, frame_height - 200)

            # Prepare label with device name and RSSI
            label = f"{device['name']} ({device['rssi']} dBm)"
            overlay_source((x, y), BLUETOOTH_ICON, label, bluetooth_color)

    return frame
