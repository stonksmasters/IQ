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

    # Function to add icon and text
    def add_hud_item(icon, text, position):
        if icon is not None:
            try:
                icon_resized = cv2.resize(icon, (icon_size, icon_size), interpolation=cv2.INTER_AREA)
                # Define region of interest (ROI)
                roi = frame[position[1]:position[1]+icon_size, position[0]:position[0]+icon_size]
                # Handle alpha channel for icons
                if icon_resized.shape[2] == 4:
                    alpha_icon = icon_resized[:, :, 3] / 255.0
                    for c in range(0, 3):
                        roi[:, :, c] = (alpha_icon * icon_resized[:, :, c] +
                                        (1 - alpha_icon) * roi[:, :, c])
                else:
                    roi[:] = icon_resized
            except Exception as e:
                logging.error(f"Error overlaying icon: {e}")
        # Put text next to icon
        cv2.putText(frame, text, (position[0] + icon_size + 10, position[1] + icon_size - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    # Overlay Wi-Fi Signals
    if wifi_signals:
        # Sort Wi-Fi networks by signal strength descending
        sorted_wifi = sorted(wifi_signals, key=lambda x: x['signal'], reverse=True)
        top_wifi = sorted_wifi[0]  # Strongest Wi-Fi network
        cv2.putText(frame, "Wi-Fi Networks:", (x_start, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        y_offset += 20
        for idx, network in enumerate(sorted_wifi):
            # Change color for the strongest network
            color = (0, 255, 0) if idx == 0 else (0, 200, 0)
            # Prepare text and signal strength
            text = f"{network['SSID']} ({network['signal']} dBm)"
            signal_strength = network['signal']
            # Draw Wi-Fi icon
            add_hud_item(WIFI_ICON, "", (x_start, y_offset))
            # Draw signal text
            cv2.putText(frame, text, (x_start + icon_size + 10, y_offset + icon_size - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            # Draw signal strength bar
            bar_length = max(int((signal_strength + 100) / 2), 0)  # Normalize dBm to 0-50
            cv2.rectangle(frame, (x_start + icon_size + 10, y_offset + 10),
                          (x_start + icon_size + 10 + bar_length, y_offset + 15),
                          color, -1)
            y_offset += line_height

    # Overlay Bluetooth Signals
    if bluetooth_signals:
        # Sort Bluetooth devices by RSSI descending
        sorted_bt = sorted(bluetooth_signals, key=lambda x: x['rssi'], reverse=True)
        top_bt = sorted_bt[0]  # Strongest Bluetooth device
        cv2.putText(frame, "Bluetooth Devices:", (x_start, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        y_offset += 20
        for idx, device in enumerate(sorted_bt):
            # Change color for the strongest device
            color = (255, 0, 0) if idx == 0 else (200, 0, 0)
            # Prepare text and signal strength
            text = f"{device['name']} ({device['address']})"
            rssi = device['rssi']
            # Draw Bluetooth icon
            add_hud_item(BLUETOOTH_ICON, "", (x_start, y_offset))
            # Draw signal text
            cv2.putText(frame, text, (x_start + icon_size + 10, y_offset + icon_size - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            # Draw RSSI bar
            bar_length = max(int((rssi + 100) / 2), 0)  # Normalize dBm to 0-50
            cv2.rectangle(frame, (x_start + icon_size + 10, y_offset + 10),
                          (x_start + icon_size + 10 + bar_length, y_offset + 15),
                          color, -1)
            y_offset += line_height

    return frame
