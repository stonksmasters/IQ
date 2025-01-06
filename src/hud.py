import cv2

def overlay_hud(frame, wifi_signals, bluetooth_signals, flipper_signals):
    y_offset = 50

    # Overlay Wi-Fi Signals
    for signal in wifi_signals:
        cv2.putText(frame, f"Wi-Fi: {signal['SSID']} ({signal['signal']})", 
                    (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        y_offset += 20

    # Overlay Bluetooth Signals
    for device in bluetooth_signals:
        name, address, rssi = device
        cv2.putText(frame, f"Bluetooth: {name} ({address}) RSSI:{rssi}", 
                    (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        y_offset += 20

    # Overlay Flipper Zero Signals
    for signal in flipper_signals:
        cv2.putText(frame, f"Flipper: {signal['type']} ({signal['frequency']}MHz)", 
                    (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        y_offset += 20

    # Example: Draw a center crosshair
    height, width, _ = frame.shape
    center_x, center_y = width // 2, height // 2
    cv2.line(frame, (center_x - 20, center_y), (center_x + 20, center_y), (0, 255, 255), 2)
    cv2.line(frame, (center_x, center_y - 20), (center_x, center_y + 20), (0, 255, 255), 2)

    return frame
