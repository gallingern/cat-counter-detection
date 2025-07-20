#!/bin/bash

# Simple Cat Detection System Installation Script
# For Raspberry Pi 2 W with Camera Module v1
#
# This script is for full installation and setup.
# For quick updates after git pull, use update.sh instead.
#
# Differences:
# - install.sh: Full system setup, package installation, service creation
# - update.sh: Git pull, dependency updates, service restart, web testing

echo "=== Simple Cat Detection System Installation ==="
echo "This script will install the necessary dependencies and set up the system."
echo ""

# Show help if requested
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --force-update    Force update package lists and install system packages"
    echo "  --force-reinstall Force recreate virtual environment and reinstall Python packages"
    echo "  --help, -h        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                # Normal install/update (optimized for speed)"
    echo "  $0 --force-update # Force update all system packages"
    echo "  $0 --force-reinstall # Force reinstall Python dependencies"
    echo ""
    exit 0
fi



# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "⚠️  Warning: This doesn't appear to be a Raspberry Pi."
    echo "    This system is designed for Raspberry Pi 2 W with Camera Module v1."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 1
    fi
fi

# Check if this is a fresh install or update
FRESH_INSTALL=false
if [ ! -d "venv" ] || [ ! -f "/etc/systemd/system/cat-detection.service" ]; then
    FRESH_INSTALL=true
    echo "🆕 Fresh installation detected"
else
    echo "🔄 Update installation detected - optimizing for speed"
fi

# Update package lists (only if fresh install or forced)
if [ "$FRESH_INSTALL" = true ] || [ "$1" = "--force-update" ]; then
    echo "📦 Updating package lists..."
    sudo apt-get update
else
    echo "📦 Skipping package list update (use --force-update to override)"
fi

# Install required packages (only if fresh install or forced)
if [ "$FRESH_INSTALL" = true ] || [ "$1" = "--force-update" ]; then
    echo "📦 Installing required packages..."
    sudo apt-get install -y python3-pip python3-opencv python3-flask python3-venv python3-full libraspberrypi-bin libraspberrypi-dev libraspberrypi0 opencv-data
else
    echo "📦 Skipping package installation (already installed)"
fi

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
if [ -d "venv" ]; then
    if [ "$FRESH_INSTALL" = true ] || [ "$1" = "--force-reinstall" ]; then
        echo "Removing existing virtual environment..."
        rm -rf venv
    else
        echo "Using existing virtual environment"
    fi
fi

if [ ! -d "venv" ]; then
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment"
        echo "Trying alternative method..."
        python3 -m pip install --user virtualenv
        python3 -m virtualenv venv
    fi
fi

# Activate virtual environment and install dependencies
echo "🐍 Installing Python dependencies..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "❌ Failed to activate virtual environment"
    exit 1
fi

# Only install dependencies if fresh install or forced
if [ "$FRESH_INSTALL" = true ] || [ "$1" = "--force-reinstall" ]; then
    echo "Installing opencv-python..."
    pip install opencv-python
    echo "Installing flask..."
    pip install flask
    echo "Installing numpy..."
    pip install numpy
else
    echo "Checking Python dependencies..."
    # Quick check if packages are installed
    if ! python -c "import cv2, flask, numpy" 2>/dev/null; then
        echo "⚠️  Some dependencies missing, installing..."
        pip install opencv-python flask numpy
    else
        echo "✅ All Python dependencies already installed"
    fi
fi

# Enable camera (only if not already enabled)
echo "📷 Checking camera module..."

# Use the standard config file location for Raspberry Pi OS 64-bit
CONFIG_FILE="/boot/firmware/config.txt"
echo "Using config file: $CONFIG_FILE"

# Check if camera settings are already enabled
CAMERA_ENABLED=false
if grep -q "^start_x=1" "$CONFIG_FILE" && grep -q "^gpu_mem=128" "$CONFIG_FILE"; then
    CAMERA_ENABLED=true
fi

if [ "$CAMERA_ENABLED" = false ]; then
    echo "Enabling camera module..."
    
    # Add essential camera settings
    if ! grep -q "^start_x=1" "$CONFIG_FILE"; then
        sudo bash -c "echo 'start_x=1' >> $CONFIG_FILE"
        echo "Added start_x=1"
    fi
    
    if ! grep -q "^gpu_mem=128" "$CONFIG_FILE"; then
        sudo bash -c "echo 'gpu_mem=128' >> $CONFIG_FILE"
        echo "Added gpu_mem=128"
    fi
    
    # Add camera auto-detect if not present
    if ! grep -q "^camera_auto_detect=1" "$CONFIG_FILE"; then
        sudo bash -c "echo 'camera_auto_detect=1' >> $CONFIG_FILE"
        echo "Added camera_auto_detect=1"
    fi
    
    # Add specific overlay for Camera Module v2 (imx219) on Pi Zero 2
    if ! grep -q "^dtoverlay=imx219" "$CONFIG_FILE"; then
        sudo bash -c "echo 'dtoverlay=imx219' >> $CONFIG_FILE"
        echo "Added dtoverlay=imx219 for Camera Module v2"
    fi
    
    # Add legacy camera support for v1 module (ov5647) as fallback
    if ! grep -q "^dtoverlay=ov5647" "$CONFIG_FILE"; then
        sudo bash -c "echo 'dtoverlay=ov5647' >> $CONFIG_FILE"
        echo "Added dtoverlay=ov5647 for legacy v1 support"
    fi
    
    # Add Pi Zero 2 specific camera settings
    if ! grep -q "^camera_interface=1" "$CONFIG_FILE"; then
        sudo bash -c "echo 'camera_interface=1' >> $CONFIG_FILE"
        echo "Added camera_interface=1 for Pi Zero 2"
    fi
    
    echo "Camera module enabled. A reboot will be required."
    REBOOT_REQUIRED=true
else
    echo "Camera module already enabled."
fi

# Create/update systemd service
echo "🔧 Creating/updating systemd service..."
# Always update the service file to ensure it has the latest configuration
# This ensures service updates are applied even during updates
sudo tee /etc/systemd/system/cat-detection.service > /dev/null << EOL
[Unit]
Description=Simple Cat Detection Service
After=network.target

[Service]
ExecStart=$(pwd)/venv/bin/python $(pwd)/start_detection.py
WorkingDirectory=$(pwd)
StandardOutput=inherit
StandardError=inherit
Restart=always
User=$USER
Environment=PYTHONPATH=$(pwd)

[Install]
WantedBy=multi-user.target
EOL

# Enable and start the service
echo "🔧 Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable cat-detection

# Only restart if service is already running
if systemctl is-active --quiet cat-detection; then
    echo "Restarting existing service..."
    sudo systemctl restart cat-detection
else
    echo "Starting new service..."
    sudo systemctl start cat-detection
fi

# Make scripts executable (this only changes file permissions, not content)
echo "🔧 Making scripts executable..."
chmod +x start_detection.py
chmod +x update.sh
chmod +x install.sh

# Test the installation
echo "🧪 Testing installation..."
source venv/bin/activate

# Fix camera permissions
echo "🔧 Fixing camera permissions..."
sudo usermod -a -G video $USER
sudo chmod 666 /dev/video* 2>/dev/null || echo "Camera devices not found yet"

# Check camera access using OpenCV
echo "🔍 Checking camera access..."
source venv/bin/activate
if python -c "import cv2; cap = cv2.VideoCapture(0); print('Camera available:', cap.isOpened()); cap.release()" 2>/dev/null; then
    echo "✅ Camera access confirmed via OpenCV"
else
    echo "⚠️  Camera access test failed - check camera connection and permissions"
fi

# Check cascade file
echo "🔍 Checking cascade file..."
CASCADE_FOUND=false
for cascade_path in "/usr/local/share/opencv4/haarcascades/haarcascade_frontalcatface.xml" "/usr/share/opencv4/haarcascades/haarcascade_frontalcatface.xml" "/usr/local/share/opencv/haarcascades/haarcascade_frontalcatface.xml" "/usr/share/opencv/haarcascades/haarcascade_frontalcatface.xml"; do
    if [ -f "$cascade_path" ]; then
        echo "✅ Found cascade file at: $cascade_path"
        CASCADE_FOUND=true
        break
    fi
done

if [ "$CASCADE_FOUND" = false ]; then
    echo "⚠️  Cascade file not found - installing opencv-data..."
    sudo apt-get install -y opencv-data
fi

# Test each package individually with better error handling
echo "Testing individual packages..."
if python -c "import cv2; print('✅ OpenCV installed')" 2>/dev/null; then
    OPENCV_OK=true
else
    echo "❌ OpenCV failed"
    OPENCV_OK=false
fi

if python -c "import flask; print('✅ Flask installed')" 2>/dev/null; then
    FLASK_OK=true
else
    echo "❌ Flask failed"
    FLASK_OK=false
fi

# Overall test result
if [ "$OPENCV_OK" = true ] && [ "$FLASK_OK" = true ]; then
    echo "✅ Core dependencies installed successfully"
    echo "✅ Installation test passed"
else
    echo "❌ Some core dependencies failed to install"
    echo "Please check the installation manually"
fi

# Print completion message
echo ""
echo "=== Installation Complete! ==="
IP_ADDRESS=$(hostname -I | awk '{print $1}')
echo "The cat detection system is now running."
echo "You can access the web interface at: http://$IP_ADDRESS:5000"
echo ""

if [ "$REBOOT_REQUIRED" = true ]; then
    echo "⚠️  A reboot is required for the camera module to be enabled."
    read -p "Reboot now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo reboot
    else
        echo "Please reboot manually when convenient."
    fi
fi