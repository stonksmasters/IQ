#/src/test_flipper.py

from flipper import fetch_flipper_data

def test_fetch_flipper_data():
    known_positions = {}  # Define known positions if needed
    data = fetch_flipper_data(known_positions)
    print("Fetched Flipper Data:", data)

if __name__ == "__main__":
    test_fetch_flipper_data()
