#!/bin/bash

# Cat Counter Detection System Installation Script
# This script installs and configures the Cat Counter Detection System on Raspberry Pi

echo "=== Cat Counter Detection System Installer ==="
echo "This script will install the Cat Counter Detection system on your Raspberry Pi."
echo ""

# Check if this is an update or a fresh install
INSTALL_TYPE="fresh"
if [ -d "venv" ] && [ -f "config.json" ]; then
    echo "Existing installation detected."
    echo "Would you like to update the existing installation? (y/n)"
    read -r do_update
    if [ "$do_update" = "y" ]; then
        INSTALL_TYPE="update"
        echo "Performing update..."
        
        # Check for git repository to pull latest changes
        if [ -d ".git" ]; then
            echo "Git repository detected. Pulling latest changes..."
            git stash  # Save any local changes
            git pull   # Pull latest changes
            echo "Repository updated to latest version."
        fi
    else
        echo "Continuing with fresh installation..."
    fi
fi

echo "Installation type: $INSTALL_TYPE"
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

# Check camera configuration
echo "Checking camera configuration..."

# First, check if camera is enabled in config - need to check both start_x=1 and gpu_mem settings
CAMERA_ENABLED=false
if grep -q "^start_x=1" /boot/config.txt 2>/dev/null || grep -q "^gpu_mem=" /boot/config.txt 2>/dev/null; then
    echo "Camera interface is enabled in configuration. ✓"
    CAMERA_ENABLED=true
else
    echo "Camera interface is not enabled in Raspberry Pi configuration."
    echo "Would you like to enable it now? (y/n)"
    read -r enable_camera
    if [ "$enable_camera" = "y" ]; then
        echo "Enabling camera interface..."
        sudo raspi-config nonint do_camera 0
        # Also set minimum GPU memory for camera
        if ! grep -q "^gpu_mem=" /boot/config.txt; then
            echo "Setting minimum GPU memory for camera..."
            echo "gpu_mem=128" | sudo tee -a /boot/config.txt
        fi
        CAMERA_ENABLED=true
        REBOOT_REQUIRED=true
    else
        echo "Warning: Camera interface not enabled. The system may not work properly."
    fi
fi

# Now check for camera module detection
echo "Checking for camera module..."
if vcgencmd get_camera | grep -q "detected=1"; then
    echo "Camera module detected. ✓"
    
    # For detected cameras, try to determine type based on Pi model
    if [ "$PI_TYPE" = "zero" ] || [ "$PI_TYPE" = "zero2" ] || [ "$PI_TYPE" = "pi3" ]; then
        echo "Assuming Camera Module v1 or v2 based on Pi model..."
        CAMERA_TYPE="v1"
    else
        echo "Assuming Camera Module v2 or newer based on Pi model..."
        CAMERA_TYPE="v2"
    fi
else
    # Only prompt for camera type if camera is not detected
    echo "Camera module not detected. This could be because:"
    echo "  1. Camera is not properly connected"
    echo "  2. Camera interface is not enabled in config"
    echo "  3. System needs to be rebooted after enabling camera"
    echo ""
    
    if [ "$CAMERA_ENABLED" = true ] && [ "$INSTALL_TYPE" = "update" ]; then
        echo "Camera interface is enabled but module not detected."
        echo "Using previously configured camera settings."
    else
        echo "Please select your camera type:"
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
    fi
fi

# Save camera type to a config file for future reference
echo "Saving camera configuration..."
mkdir -p .kiro/settings
echo "CAMERA_TYPE=$CAMERA_TYPE" > .kiro/settings/camera_config

# Install camera-specific packages
echo "Installing camera support packages..."
if [ "$CAMERA_TYPE" = "v1" ]; then
    # For Camera Module v1, try to install python3-picamera from apt
    sudo apt-get install -y python3-picamera || echo "Warning: python3-picamera not available from apt"
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
if [ "$INSTALL_TYPE" = "update" ] && [ -d "venv" ]; then
    echo "Using existing virtual environment..."
    source venv/bin/activate
    
    # Update pip in the virtual environment
    echo "Updating pip in virtual environment..."
    pip install --upgrade pip
else
    echo "Creating new virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    
    # Install latest pip in the new virtual environment
    echo "Installing latest pip in virtual environment..."
    pip install --upgrade pip
fi

# Create a modified requirements file without the problematic packages
echo "Creating modified requirements file..."
grep -v "tflite-runtime" requirements.txt > requirements_modified.txt
grep -v "picamera2" requirements_modified.txt > requirements_modified_temp.txt
mv requirements_modified_temp.txt requirements_modified.txt

# Install the modified requirements
echo "Installing dependencies from modified requirements file..."
if [ "$INSTALL_TYPE" = "update" ]; then
    echo "Updating Python dependencies..."
    pip install --upgrade -r requirements_modified.txt
else
    echo "Installing Python dependencies..."
    pip install -r requirements_modified.txt
fi

# Install TensorFlow Lite runtime with the correct version for Raspberry Pi
echo "Installing TensorFlow Lite runtime..."

# Get Python version for wheel selection
python_version_for_wheel=$(python3 -c 'import sys; print(f"{sys.version_info.major}{sys.version_info.minor}")')
echo "Detected Python version for wheel: $python_version_for_wheel"

# Try to install tflite-runtime using pip
pip install tflite-runtime || {
    echo "Standard tflite-runtime installation failed. Trying alternative methods..."
    
    # Try to find a compatible wheel based on Python version and architecture
    if [ "$python_version_for_wheel" = "311" ]; then
        echo "Using compatible wheel for Python 3.11..."
        pip install --extra-index-url https://google-coral.github.io/py-repo/ tflite_runtime || echo "Warning: TensorFlow Lite installation failed. The system will continue without TensorFlow Lite support."
    elif [ "$python_version_for_wheel" = "39" ]; then
        echo "Using compatible wheel for Python 3.9..."
        pip install https://github.com/google-coral/pycoral/releases/download/v2.0.0/tflite_runtime-2.5.0.post1-cp39-cp39-linux_aarch64.whl || echo "Warning: TensorFlow Lite installation failed. The system will continue without TensorFlow Lite support."
    else
        echo "Warning: No compatible TensorFlow Lite wheel found for Python $python_version_for_wheel. The system will continue without TensorFlow Lite support."
    fi
}

# Install picamera or picamera2 based on camera type
echo "Installing camera libraries..."
if [ "$CAMERA_TYPE" = "v1" ]; then
    # For Camera Module v1, use picamera
    pip install picamera
else
    # For newer camera modules, try picamera2
    pip install picamera2 || echo "Warning: picamera2 installation failed. You may need to install it manually."
fi

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