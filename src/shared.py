#/src/shared.py

import threading

# Shared data structures
signals_lock = threading.Lock()
signals_data = {
    "wifi": [],
    "bluetooth": [],
    "subghz": [],
    "nfc": [],
    "rfid": []
}
selected_signal = {"type": None, "name": None, "position": None}
