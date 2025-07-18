#!/bin/bash

# Cat Counter Detection System Installation Script
# This script installs and configures the Cat Counter Detection System on Raspberry Pi

echo "=== Cat Counter Detection System Installer ==="
echo "This script will install the Cat Counter Detection system on your Raspberry Pi."
echo ""

# Check if running on Raspberry Pi
if [ ! -e /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model; then
    echo "Warning: This doesn't appear to be a Raspberry Pi. The system is optimized for Raspberry Pi hardware."
    echo "Do you want to continue anyway? (y/n)"
    read -r continue_install
    if [ "$continue_install" != "y" ]; then
        echo "Installation cancelled."
        exit 1
    fi
fi

# Check for Python 3.7+
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "Python 3 not found. Would you like to install Python 3.9? (y/n)"
    read -r install_python
    if [ "$install_python" = "y" ]; then
        echo "Installing Python 3.9..."
        sudo apt-get update
        sudo apt-get install -y python3.9 python3.9-venv python3.9-dev python3-pip
        sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1
        echo "Python 3.9 installed successfully."
    else
        echo "Installation cancelled. Python 3.7 or newer is required."
        exit 1
    fi
fi

python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
python_version_major=$(echo "$python_version" | cut -d. -f1)
python_version_minor=$(echo "$python_version" | cut -d. -f2)

# Check if Python version is at least 3.7
if [ "$python_version_major" -lt 3 ] || ([ "$python_version_major" -eq 3 ] && [ "$python_version_minor" -lt 7 ]); then
    echo "Python version $python_version detected. Version 3.7 or newer is required."
    echo "Would you like to install Python 3.9? (y/n)"
    read -r install_python
    if [ "$install_python" = "y" ]; then
        echo "Installing Python 3.9..."
        sudo apt-get update
        sudo apt-get install -y python3.9 python3.9-venv python3.9-dev python3-pip
        sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1
        echo "Python 3.9 installed successfully."
        # Update python_version after installation
        python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    else
        echo "Installation cancelled. Python 3.7 or newer is required."
        exit 1
    fi
fi
echo "Python $python_version detected. ✓"

# Check for camera prerequisites
echo "Checking for camera prerequisites..."

# Check if camera interface is enabled
if ! command -v vcgencmd &> /dev/null; then
    echo "Camera utilities not found. Installing camera prerequisites..."
    sudo apt-get update
    sudo apt-get install -y libraspberrypi-bin
fi

# Check if camera is enabled in config
if ! grep -q "^start_x=1" /boot/config.txt 2>/dev/null; then
    echo "Camera interface is not enabled in Raspberry Pi configuration."
    echo "Would you like to enable it now? (y/n)"
    read -r enable_camera
    if [ "$enable_camera" = "y" ]; then
        echo "Enabling camera interface..."
        sudo raspi-config nonint do_camera 0
        echo "Camera interface enabled. A reboot will be required after installation."
        REBOOT_REQUIRED=true
    else
        echo "Warning: Camera interface not enabled. The system may not work properly."
    fi
fi

# Check for camera module
echo "Checking for camera module..."
if ! vcgencmd get_camera | grep -q "detected=1"; then
    echo "Warning: Camera module not detected. This could be due to:"
    echo "  - Camera not properly connected"
    echo "  - Camera ribbon cable not properly seated"
    echo "  - Camera module hardware issue"
    echo ""
    echo "Do you want to continue anyway? (y/n)"
    read -r continue_install
    if [ "$continue_install" != "y" ]; then
        echo "Installation cancelled."
        exit 1
    fi
fi

# Create required directories
echo "Creating required directories..."
mkdir -p data/images
mkdir -p logs

# Install required packages
echo "Installing required packages..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-opencv libatlas-base-dev libhdf5-dev libhdf5-serial-dev libjasper-dev libqtgui4 libqt4-test

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Set up configuration
echo "Setting up configuration..."
if [ ! -f config.json ]; then
    cp config.example.json config.json
    echo "Default configuration created at config.json"
    echo "Please edit this file to configure your notification preferences."
fi

# Set up systemd service
echo "Setting up systemd service..."
sudo tee /etc/systemd/system/cat-detection.service > /dev/null << EOL
[Unit]
Description=Cat Counter Detection Service
After=network.target

[Service]
ExecStart=$(which python3) $(pwd)/cat_counter_detection/detection_pipeline.py
WorkingDirectory=$(pwd)
StandardOutput=inherit
StandardError=inherit
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
EOL

sudo systemctl daemon-reload
sudo systemctl enable cat-detection.service

echo ""
echo "=== Installation Complete ==="
echo "To start the service, run: sudo systemctl start cat-detection"
echo "To view the web interface, navigate to: http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "Thank you for installing the Cat Counter Detection System!"