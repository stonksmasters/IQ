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
    # Define positions and sizes
    x_start = 10
    y_start = 30
    line_height = 30
    icon_size = 24  # Size to resize icons

    # Overlay semi-transparent rectangle as background for HUD
    overlay = frame.copy()
    cv2.rectangle(overlay, (5, 5), (350, 250), (0, 0, 0), -1)
    alpha = 0.4  # Transparency factor
    frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

    y_offset = y_start

    # Function to add icon and text with boundary checks
    def add_hud_item(icon, text, position):
        if icon is not None:
            try:
                icon_resized = cv2.resize(icon, (icon_size, icon_size), interpolation=cv2.INTER_AREA)
                # Define region of interest (ROI)
                roi_y_start = position[1]
                roi_y_end = position[1] + icon_size
                roi_x_start = position[0]
                roi_x_end = position[0] + icon_size

                # Get frame dimensions
                frame_height, frame_width = frame.shape[:2]

                # Boundary checks
                if roi_y_end > frame_height or roi_x_end > frame_width or roi_y_start < 0 or roi_x_start < 0:
                    logging.warning(f"Overlay position {position} with size {icon_size}x{icon_size} exceeds frame boundaries.")
                    return  # Skip overlaying this icon

                roi = frame[roi_y_start:roi_y_end, roi_x_start:roi_x_end]

                # Handle alpha channel for icons
                if icon_resized.shape[2] == 4:
                    alpha_icon = icon_resized[:, :, 3] / 255.0
                    for c in range(0, 3):
                        roi[:, :, c] = (alpha_icon * icon_resized[:, :, c] +
                                        (1 - alpha_icon) * roi[:, :, c])
                else:
                    roi[:] = icon_resized
            except Exception as e:
                logging.error(f"Error overlaying icon at position {position}: {e}")

        # Put text next to icon
        text_x = position[0] + icon_size + 10
        text_y = position[1] + icon_size - 5

        # Ensure text does not exceed frame boundaries
        if text_x >= frame_width or text_y >= frame_height:
            logging.warning(f"Text position ({text_x}, {text_y}) exceeds frame boundaries.")
            return  # Skip putting text

        cv2.putText(frame, text, (text_x, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    frame_height, frame_width = frame.shape[:2]

    # Overlay Wi-Fi Signals
    if wifi_signals:
        logging.info(f"Overlaying {len(wifi_signals)} Wi-Fi networks.")
        # Sort Wi-Fi networks by signal strength descending
        sorted_wifi = sorted(wifi_signals, key=lambda x: x['signal'], reverse=True)
        for idx, network in enumerate(sorted_wifi):
            # Change color for the strongest network
            color = (0, 255, 0) if idx == 0 else (0, 200, 0)
            # Prepare text and signal strength
            text = f"{network['SSID']} ({network['signal']} dBm)"
            signal_strength = network['signal']
            # Calculate position
            position = (x_start, y_offset)
            add_hud_item(WIFI_ICON, text, position)
            y_offset += line_height

    # Reset y_offset for Bluetooth
    y_offset = y_start + len(wifi_signals) * line_height + 20

    # Overlay Bluetooth Signals
    if bluetooth_signals:
        logging.info(f"Overlaying {len(bluetooth_signals)} Bluetooth devices.")
        # Sort Bluetooth devices by RSSI descending
        sorted_bt = sorted(bluetooth_signals, key=lambda x: x['rssi'], reverse=True)
        for idx, device in enumerate(sorted_bt):
            # Change color for the strongest device
            color = (255, 0, 0) if idx == 0 else (200, 0, 0)
            # Prepare text and signal strength
            text = f"{device['name']} ({device['address']})"
            rssi = device['rssi']
            # Calculate position
            position = (x_start, y_offset)
            add_hud_item(BLUETOOTH_ICON, text, position)
            y_offset += line_height

    return frame
