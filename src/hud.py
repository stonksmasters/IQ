# src/hud.py

import cv2

def overlay_hud(frame, wifi_signals, bluetooth_signals, flipper_signals):
    """
    Overlays Wi-Fi and Bluetooth signals on the video frame.
    """
    y_offset = 50

    # Overlay Wi-Fi signals
    for network in wifi_signals:
        cv2.putText(frame, f"Wi-Fi: {network['SSID']} ({network['signal']} dBm)", 
                    (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        y_offset += 20

    # Overlay Bluetooth signals
    for device in bluetooth_signals:
        cv2.putText(frame, f"Bluetooth: {device['name']} ({device['address']}) RSSI: {device['rssi']} dBm", 
                    (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        y_offset += 20

    return frame
