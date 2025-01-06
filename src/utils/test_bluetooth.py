# src/utils/test_bluetooth.py

from signal_detection import detect_bluetooth

if __name__ == "__main__":
    devices = detect_bluetooth()
    print("Detected Bluetooth devices:")
    for device in devices:
        print(f"Name: {device['name']}, Address: {device['address']}, RSSI: {device['rssi']} dBm")
