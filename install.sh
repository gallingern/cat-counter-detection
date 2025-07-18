#!/bin/bash

# Simple Cat Detection System Installation Script
# For Raspberry Pi 2 W with Camera Module v1

echo "=== Simple Cat Detection System Installation ==="
echo "This script will install the necessary dependencies and set up the system."
echo ""

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

# Update package lists
echo "📦 Updating package lists..."
sudo apt-get update

# Install required packages
echo "📦 Installing required packages..."
sudo apt-get install -y python3-pip python3-opencv python3-flask python3-venv python3-full

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment and install dependencies
echo "🐍 Installing Python dependencies..."
source venv/bin/activate
pip install picamera opencv-python flask numpy

# Enable camera
echo "📷 Enabling camera module..."
if ! grep -q "^start_x=1" /boot/config.txt; then
    sudo bash -c 'echo "start_x=1" >> /boot/config.txt'
    sudo bash -c 'echo "gpu_mem=128" >> /boot/config.txt'
    echo "Camera module enabled. A reboot will be required."
    REBOOT_REQUIRED=true
else
    echo "Camera module already enabled."
fi

# Create systemd service
echo "🔧 Creating systemd service..."
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

[Install]
WantedBy=multi-user.target
EOL

# Enable and start the service
echo "🔧 Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable cat-detection
sudo systemctl start cat-detection

# Make scripts executable
chmod +x start_detection.py
chmod +x update.sh

# Test the installation
echo "🧪 Testing installation..."
if python3 -c "import cv2, flask; print('✅ Dependencies installed successfully')" 2>/dev/null; then
    echo "✅ Installation test passed"
else
    echo "❌ Installation test failed - checking virtual environment..."
    if source venv/bin/activate && python -c "import cv2, flask; print('✅ Virtual environment test passed')" 2>/dev/null; then
        echo "✅ Virtual environment is working correctly"
    else
        echo "❌ Virtual environment test failed"
        echo "Please check the installation manually"
    fi
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