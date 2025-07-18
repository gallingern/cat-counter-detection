#!/bin/bash

# Cat Counter Detection System Installation Script
# This script installs and configures the Cat Counter Detection System on Raspberry Pi

echo "=== Cat Counter Detection System Installer ==="
echo "This script will install the Cat Counter Detection system on your Raspberry Pi."
echo ""

# Initialize reboot flag
REBOOT_REQUIRED=false

# Detect Raspberry Pi model
echo "Detecting Raspberry Pi model..."
if [ -e /proc/device-tree/model ]; then
    PI_MODEL=$(tr -d '\0' < /proc/device-tree/model)
    echo "Detected: $PI_MODEL"
    
    # Extract Pi version for specific optimizations
    if [[ "$PI_MODEL" == *"Zero W"* ]]; then
        PI_TYPE="zero"
        echo "Optimizing for Raspberry Pi Zero W..."
    elif [[ "$PI_MODEL" == *"Zero 2 W"* ]]; then
        PI_TYPE="zero2"
        echo "Optimizing for Raspberry Pi Zero 2 W..."
    elif [[ "$PI_MODEL" == *"Pi 3"* ]]; then
        PI_TYPE="pi3"
        echo "Optimizing for Raspberry Pi 3..."
    elif [[ "$PI_MODEL" == *"Pi 4"* ]]; then
        PI_TYPE="pi4"
        echo "Optimizing for Raspberry Pi 4..."
    elif [[ "$PI_MODEL" == *"Pi 5"* ]]; then
        PI_TYPE="pi5"
        echo "Optimizing for Raspberry Pi 5..."
    else
        PI_TYPE="generic"
        echo "Using generic Raspberry Pi optimizations..."
    fi
else
    echo "Warning: This doesn't appear to be a Raspberry Pi. The system is optimized for Raspberry Pi hardware."
    echo "Do you want to continue anyway? (y/n)"
    read -r continue_install
    if [ "$continue_install" != "y" ]; then
        echo "Installation cancelled."
        exit 1
    fi
    PI_TYPE="generic"
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

# Check for camera module
echo "Checking for camera module..."
if ! vcgencmd get_camera | grep -q "detected=1"; then
    echo "Camera module not detected. Please select your camera type:"
    echo "1) Camera Module v1 (Original 5MP camera)"
    echo "2) Camera Module v2 (8MP camera)"
    echo "3) Camera Module v3 (12MP camera)"
    echo "4) High Quality Camera (12.3MP)"
    echo "5) Other/Not sure"
    read -p "Enter your choice [1-5]: " camera_choice
    
    case $camera_choice in
        1)
            echo "Setting up for Camera Module v1..."
            CAMERA_TYPE="v1"
            # Install Camera Module v1 specific packages
            sudo apt-get install -y python3-picamera
            
            # Check if legacy camera stack is enabled (required for Camera Module v1)
            if ! grep -q "^camera_auto_detect=0" /boot/config.txt 2>/dev/null; then
                echo "Legacy camera stack is required for Camera Module v1."
                echo "Enabling legacy camera stack..."
                sudo raspi-config nonint do_legacy 0
                REBOOT_REQUIRED=true
            fi
            ;;
        2)
            echo "Setting up for Camera Module v2..."
            CAMERA_TYPE="v2"
            # For v2, we can use either stack, but libcamera is recommended
            if grep -q "^camera_auto_detect=0" /boot/config.txt 2>/dev/null; then
                echo "Note: You're using the legacy camera stack. Camera Module v2 works with both stacks."
            fi
            ;;
        3)
            echo "Setting up for Camera Module v3..."
            CAMERA_TYPE="v3"
            # v3 requires the new libcamera stack
            if grep -q "^camera_auto_detect=0" /boot/config.txt 2>/dev/null; then
                echo "Camera Module v3 requires the new camera stack."
                echo "Disabling legacy camera stack..."
                sudo sed -i '/camera_auto_detect=0/d' /boot/config.txt
                REBOOT_REQUIRED=true
            fi
            ;;
        4)
            echo "Setting up for High Quality Camera..."
            CAMERA_TYPE="hq"
            # HQ camera works with both stacks, but libcamera is recommended
            ;;
        5|*)
            echo "Using default camera configuration..."
            CAMERA_TYPE="generic"
            ;;
    esac
    
    # Check if camera is enabled in config
    if ! grep -q "^start_x=1" /boot/config.txt 2>/dev/null; then
        echo "Camera interface is not enabled in Raspberry Pi configuration."
        echo "Enabling camera interface..."
        sudo raspi-config nonint do_camera 0
        REBOOT_REQUIRED=true
    fi
    
    echo "Camera configuration complete. A reboot may be required to detect the camera."
else
    echo "Camera module detected. ✓"
    
    # Check if we need to install specific packages based on detected camera
    if [ "$PI_TYPE" = "zero" ] || [ "$PI_TYPE" = "pi3" ]; then
        # Older Pi models likely use Camera Module v1 or v2
        echo "Installing camera support packages..."
        sudo apt-get install -y python3-picamera
    fi
fi

# Check if camera is enabled in config (regardless of detection)
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

# Create required directories
echo "Creating required directories..."
mkdir -p data/images
mkdir -p logs

# Install required packages
echo "Installing required packages..."
sudo apt-get update
# Updated package list for newer Raspberry Pi OS versions
sudo apt-get install -y python3-pip python3-opencv python3-venv python3-full libatlas-base-dev libhdf5-dev

# Set up virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies in virtual environment..."
pip install --upgrade pip
pip install -r requirements.txt

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
ExecStart=$(pwd)/venv/bin/python $(pwd)/cat_counter_detection/detection_pipeline.py
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

# Check if reboot is required
if [ "$REBOOT_REQUIRED" = true ]; then
    echo "A reboot is required for the camera configuration changes to take effect."
    echo "Would you like to reboot now? (y/n)"
    read -r do_reboot
    if [ "$do_reboot" = "y" ]; then
        echo "Rebooting system..."
        echo "After reboot, you can start the service with: sudo systemctl start cat-detection"
        echo "Thank you for installing the Cat Counter Detection System!"
        sudo reboot
    else
        echo "Please remember to reboot your system before using the camera."
        echo "After rebooting, start the service with: sudo systemctl start cat-detection"
        echo "To view the web interface, navigate to: http://$(hostname -I | awk '{print $1}'):5000"
    fi
else
    echo "To start the service, run: sudo systemctl start cat-detection"
    echo "To view the web interface, navigate to: http://$(hostname -I | awk '{print $1}'):5000"
    echo ""
    echo "Thank you for installing the Cat Counter Detection System!"
fi