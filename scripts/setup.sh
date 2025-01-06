#!/bin/bash

# Update and upgrade the system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Install required libraries
pip3 install -r requirements.txt

# Enable necessary interfaces
sudo raspi-config nonint do_camera 0

# Reboot to apply changes
sudo reboot
