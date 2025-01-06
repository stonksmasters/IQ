# src/hud.py

import cv2
import numpy as np

# Load icons once to improve performance
WIFI_ICON = cv2.imread('src/static/images/icons/wifi_icon.png', cv2.IMREAD_UNCHANGED)
BLUETOOTH_ICON = cv2.imread('src/static/images/icons/bluetooth_icon.png', cv2.IMREAD_UNCHANGED)

def overlay_hud(frame, wifi_signals, bluetooth_signals, flipper_signals):
    """
    Overlays Wi-Fi and Bluetooth signals on the video frame with enhanced visuals.
    """
    # Define positions
    x_start = 10
    y_start = 30
    line_height = 30
    icon_size = 24  # Size to resize icons

    # Overlay semi-transparent rectangle as background for HUD
    overlay = frame.copy()
    cv2.rectangle(overlay, (5, 5), (300, 200), (0, 0, 0), -1)
    alpha = 0.4  # Transparency factor
    frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

    y_offset = y_start

    # Function to add icon and text
    def add_hud_item(icon, text, position):
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
        # Put text next to icon
        cv2.putText(frame, text, (position[0] + icon_size + 10, position[1] + icon_size - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    # Overlay Wi-Fi Signals
    if wifi_signals:
        cv2.putText(frame, "Wi-Fi Networks:", (x_start, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        y_offset += 10
        for network in wifi_signals:
            # Prepare text and signal strength
            text = f"{network['SSID']} ({network['signal']} dBm)"
            signal_strength = int(network['signal'])
            # Draw Wi-Fi icon
            add_hud_item(WIFI_ICON, "", (x_start, y_offset))
            # Draw signal text
            cv2.putText(frame, text, (x_start + icon_size + 10, y_offset + icon_size - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            # Draw signal strength bar
            bar_length = int((signal_strength + 100) / 2)  # Normalize dBm to 0-50
            cv2.rectangle(frame, (x_start + icon_size + 10, y_offset + 10),
                          (x_start + icon_size + 10 + bar_length, y_offset + 15),
                          (0, 255, 0), -1)
            y_offset += line_height

    # Overlay Bluetooth Signals
    if bluetooth_signals:
        cv2.putText(frame, "Bluetooth Devices:", (x_start, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        y_offset += 10
        for device in bluetooth_signals:
            # Prepare text and signal strength
            text = f"{device['name']} ({device['address']})"
            rssi = int(device['rssi'])
            # Draw Bluetooth icon
            add_hud_item(BLUETOOTH_ICON, "", (x_start, y_offset))
            # Draw signal text
            cv2.putText(frame, text, (x_start + icon_size + 10, y_offset + icon_size - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            # Draw RSSI bar
            bar_length = int((rssi + 100) / 2)  # Normalize dBm to 0-50
            cv2.rectangle(frame, (x_start + icon_size + 10, y_offset + 10),
                          (x_start + icon_size + 10 + bar_length, y_offset + 15),
                          (255, 0, 0), -1)
            y_offset += line_height

    return frame
