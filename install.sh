#!/usr/bin/env bash
# install.sh — Install dependencies and configure camera for IMX219 on Pi Zero 2 W

set -e

# Simple Cat Detection System Installation Script
# For Raspberry Pi Zero 2 W with Camera Module v2
#
# This script performs a complete fresh installation and setup.

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
    echo "    This system is designed for Raspberry Pi Zero 2 W with Camera Module v2."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 1
    fi
fi

# Check if this is a fresh install or update
FRESH_INSTALL=false
REBOOT_REQUIRED=false
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
    sudo apt-get install -y python3-pip python3-opencv python3-flask python3-venv python3-full libraspberrypi-bin libraspberrypi-dev libraspberrypi0 opencv-data libcamera-tools
else
    echo "📦 Skipping package installation (already installed)"
fi

# Ensure Haar cascade file for cat detection is present
echo "🔍 Ensuring Haar cascade file for cat detection is installed..."
CASCADE_DEST="/usr/local/share/opencv4/haarcascades/haarcascade_frontalcatface.xml"
if [ ! -f "$CASCADE_DEST" ] && ! ls /usr/share/opencv*/haarcascades/haarcascade_frontalcatface.xml 1>/dev/null 2>&1; then
    echo "Downloading haarcascade_frontalcatface.xml to $CASCADE_DEST"
    sudo mkdir -p "$(dirname "$CASCADE_DEST")"
    sudo curl -fsSL -o "$CASCADE_DEST" https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalcatface.xml
    if [ -f "$CASCADE_DEST" ]; then
        echo "✅ Haar cascade file installed."
    else
        echo "❌ Failed to download Haar cascade file!"
        exit 1
    fi
else
    echo "✅ Haar cascade file already present."
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
    if ! python3 -m venv --system-site-packages venv; then
        echo "❌ Failed to create virtual environment"
        echo "Trying alternative method..."
        python3 -m pip install --user virtualenv
        python3 -m virtualenv venv
    fi
fi
# Activate virtual environment and install dependencies
echo "🐍 Installing Python dependencies..."
if ! source venv/bin/activate; then
    echo "❌ Failed to activate virtual environment"
    exit 1
fi
# Only install Flask in virtual environment - use system OpenCV and numpy
if [ "$FRESH_INSTALL" = true ] || [ "$1" = "--force-reinstall" ]; then
    echo "Installing flask (using system OpenCV and numpy)..."
    pip install --upgrade flask
else
    echo "Checking Python dependencies..."
    if ! python -c "import cv2, flask, numpy" 2>/dev/null; then
        echo "⚠️  Some dependencies missing, installing flask..."
        pip install --upgrade flask
    else
        echo "✅ All Python dependencies already installed"
    fi
fi

# Configure camera module
echo "📷 Configuring camera module..."

# Determine which config file is used on this system
if [ -f "/boot/firmware/config.txt" ]; then
    CONFIG_FILE="/boot/firmware/config.txt"
else
    CONFIG_FILE="/boot/config.txt"
fi
echo "Using config file: $CONFIG_FILE"
CAMERA_CHANGES=false

# Add essential camera settings
if ! grep -q "^start_x=1" "$CONFIG_FILE"; then
    sudo bash -c "echo 'start_x=1' >> $CONFIG_FILE"
    echo "Added start_x=1"
    CAMERA_CHANGES=true
fi

if ! grep -q "^gpu_mem=128" "$CONFIG_FILE"; then
    sudo bash -c "echo 'gpu_mem=128' >> $CONFIG_FILE"
    echo "Added gpu_mem=128"
    CAMERA_CHANGES=true
fi

# Add camera auto-detect if not present
if ! grep -q "^camera_auto_detect=1" "$CONFIG_FILE"; then
    sudo bash -c "echo 'camera_auto_detect=1' >> $CONFIG_FILE"
    echo "Added camera_auto_detect=1"
    CAMERA_CHANGES=true
fi

# Add specific overlay for Camera Module v2 (imx219) on Pi Zero 2
if ! grep -q "^dtoverlay=imx219" "$CONFIG_FILE"; then
    sudo bash -c "echo 'dtoverlay=imx219' >> $CONFIG_FILE"
    echo "Added dtoverlay=imx219 for Camera Module v2"
    CAMERA_CHANGES=true
fi

if [ "$CAMERA_CHANGES" = true ]; then
    echo "Camera module configuration updated. A reboot will be required."
    REBOOT_REQUIRED=true
else
    echo "Camera module already properly configured."
fi

# Create/update systemd service
echo "🔧 Creating/updating systemd service..."
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

# Make scripts executable
echo "🔧 Making scripts executable..."
chmod +x start_detection.py
chmod +x update.sh
chmod +x install.sh

# Fix camera permissions
echo "🔧 Fixing camera permissions..."
sudo usermod -a -G video "$USER"

# Create udev rule to automatically set camera permissions
echo "📝 Creating udev rule for camera permissions..."
sudo tee /etc/udev/rules.d/99-camera-permissions.rules > /dev/null << EOL
# Set camera device permissions for video group
SUBSYSTEM=="video4linux", GROUP="video", MODE="0666"
EOL

# Apply udev rules immediately
sudo udevadm control --reload-rules
sudo udevadm trigger

# Also try to set permissions on existing devices (if any)
sudo chmod 666 /dev/video* 2>/dev/null || echo "Camera devices not found yet (will be set after reboot)"

# Test the installation
echo "🧪 Testing installation..."

# Test Python packages
echo "Testing Python packages..."
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

# Test camera access
echo "Testing camera access..."
CAMERA_OK=false
if python -c "import cv2; cap = cv2.VideoCapture(0); print('Camera available:', cap.isOpened()); cap.release()" 2>/dev/null; then
    echo "✅ Camera access confirmed via OpenCV"
    CAMERA_OK=true
else
    echo "⚠️  Camera access test failed - check camera connection and permissions"
    echo "   This is normal if camera settings were just updated and reboot is needed"
fi

# Check cascade file
echo "Checking cascade file..."
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

# Overall test result
if [ "$OPENCV_OK" = true ] && [ "$FLASK_OK" = true ]; then
    echo "✅ Core dependencies installed successfully"
    echo "✅ Installation test passed"
    
    if [ "$CAMERA_OK" = false ] && [ "$REBOOT_REQUIRED" = true ]; then
        echo "⚠️  Camera test failed but this is expected after config changes"
        echo "   Camera will work after reboot"
    fi
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

# Camera setup steps for IMX219 on Pi Zero 2 W

# 1–4. Apply unified diff to /boot/firmware/config.txt
sudo patch /boot/firmware/config.txt << 'EOF'
--- a/config.txt
+++ b/config.txt
@@
-dtoverlay=vc4-fkms-v3d
+dtoverlay=vc4-kms-v3d
@@
-#disable_fw_kms_setup=1
+#disable_fw_kms_setup=1
@@ [all]
-start_x=1
-dtoverlay=imx219
+#start_x=1
+#dtoverlay=imx219
@@
-#dtparam=i2c_arm=on
+dtparam=i2c_arm=on
@@
+# Tell the kernel there’s an IMX219 on I²C-1
+dtoverlay=imx219
@@ [all]
-gpu_mem=64
+gpu_mem=128
EOF

# 5. Add udev rule for /dev/vcio
sudo tee /etc/udev/rules.d/99-vcio.rules << 'EOF'
KERNEL=="vcio", MODE="0666"
EOF

# 5. Add udev rule for /dev/dma_heap
sudo tee /etc/udev/rules.d/99-dma_heap.rules << 'EOF'
SUBSYSTEM=="dma_heap", GROUP="video", MODE="0660"
EOF

# 5. Add 'pi' user to 'video' group
sudo usermod -aG video pi

# 6. Reload udev rules and reboot
sudo udevadm control --reload-rules
sudo udevadm trigger
sudo reboot
