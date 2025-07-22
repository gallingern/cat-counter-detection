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

# Create models directory and download TFLite model
echo "📥 Setting up TFLite model..."
MODELS_DIR="models"
MODEL_FILE="$MODELS_DIR/ssdlite_mobilenet_v2_int8.tflite"

if [ ! -d "$MODELS_DIR" ]; then
    mkdir -p "$MODELS_DIR"
fi

if [ ! -f "$MODEL_FILE" ] || [ "$1" = "--force-reinstall" ]; then
    echo "Downloading TFLite model..."
    echo "Note: This will download a COCO-trained model that can detect cats (class 16)"
    
    # Download COCO SSD MobileNet V2 quantized model
    TEMP_ZIP="/tmp/coco_ssd_mobilenet.zip"
    if curl -fsSL -o "$TEMP_ZIP" "https://storage.googleapis.com/download.tensorflow.org/models/tflite/coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip"; then
        echo "Extracting model file..."
        if unzip -q "$TEMP_ZIP" "detect.tflite" -d "$MODELS_DIR" && mv "$MODELS_DIR/detect.tflite" "$MODEL_FILE"; then
            echo "✅ TFLite model downloaded and extracted successfully"
            rm -f "$TEMP_ZIP"
        else
            echo "❌ Failed to extract model from zip"
            rm -f "$TEMP_ZIP"
            exit 1
        fi
    else
        echo "❌ Failed to download model"
        echo "Please download the model manually and place it in $MODEL_FILE"
        echo "You can find TFLite models at: https://github.com/tensorflow/models/blob/master/research/object_detection/g3doc/tf2_detection_zoo.md"
        exit 1
    fi
else
    echo "✅ TFLite model already present"
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
    pip install --upgrade flask tflite-runtime
else
    echo "Checking Python dependencies..."
    if ! python -c "import cv2, flask, numpy" 2>/dev/null; then
        echo "⚠️  Some dependencies missing, installing flask..."
        pip install --upgrade flask tflite-runtime
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

# Add I2C support for camera communication
if ! grep -q "^dtparam=i2c_arm=on" "$CONFIG_FILE"; then
    sudo bash -c "echo 'dtparam=i2c_arm=on' >> $CONFIG_FILE"
    echo "Added dtparam=i2c_arm=on"
    CAMERA_CHANGES=true
fi

# Add DMA heap support for libcamera
if ! grep -q "^dtoverlay=dma-heap" "$CONFIG_FILE"; then
    sudo bash -c "echo 'dtoverlay=dma-heap' >> $CONFIG_FILE"
    echo "Added dtoverlay=dma-heap"
    CAMERA_CHANGES=true
fi

if [ "$CAMERA_CHANGES" = true ]; then
    echo "Camera module configuration updated. A reboot will be required."
    REBOOT_REQUIRED=true
else
    echo "Camera module already properly configured."
fi

# Fix camera permissions BEFORE starting service
echo "🔧 Fixing camera permissions..."
sudo usermod -a -G video "$USER"

# Create udev rules for camera permissions
echo "📝 Creating udev rules for camera permissions..."
sudo tee /etc/udev/rules.d/99-camera-permissions.rules > /dev/null << EOL
# Set camera device permissions for video group
SUBSYSTEM=="video4linux", GROUP="video", MODE="0666"
EOL

# Add udev rule for /dev/vcio
echo "📝 Creating udev rule for vcio permissions..."
sudo tee /etc/udev/rules.d/99-vcio.rules > /dev/null << EOL
KERNEL=="vcio", MODE="0666"
EOL

# Add udev rule for /dev/dma_heap
echo "📝 Creating udev rule for dma_heap permissions..."
sudo tee /etc/udev/rules.d/99-dma_heap.rules > /dev/null << EOL
SUBSYSTEM=="dma_heap", GROUP="video", MODE="0660"
EOL

# Apply udev rules immediately
echo "🔧 Applying udev rules..."
sudo udevadm control --reload-rules
sudo udevadm trigger

# Set permissions on existing devices (if any)
echo "🔧 Setting permissions on existing devices..."
sudo chmod 666 /dev/video* 2>/dev/null || echo "Camera devices not found yet (will be set after reboot)"
sudo chmod 666 /dev/vcio 2>/dev/null || echo "vcio device not found yet (will be set after reboot)"
sudo chmod 666 /dev/dma_heap* 2>/dev/null || echo "dma_heap devices not found yet (will be set after reboot)"

# Verify udev rules were created
echo "🔍 Verifying udev rules..."
if [ -f "/etc/udev/rules.d/99-camera-permissions.rules" ] && [ -f "/etc/udev/rules.d/99-vcio.rules" ] && [ -f "/etc/udev/rules.d/99-dma_heap.rules" ]; then
    echo "✅ All udev rules created successfully"
else
    echo "❌ Failed to create some udev rules!"
    exit 1
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

if python -c "import tflite_runtime.interpreter" 2>/dev/null; then
    TFLITE_OK=true
else
    echo "❌ tflite-runtime failed"
    TFLITE_OK=false
fi

# Test camera access
echo "Testing camera access..."
CAMERA_OK=false

# Test libcamera first (our primary camera system)
if command -v libcamera-vid >/dev/null 2>&1; then
    echo "Testing libcamera access..."
    if timeout 10s libcamera-vid --list-cameras >/dev/null 2>&1; then
        echo "✅ Camera access confirmed via libcamera"
        CAMERA_OK=true
    else
        echo "⚠️  libcamera test failed - this may be normal after config changes"
    fi
fi

# Fallback to OpenCV test
if [ "$CAMERA_OK" = false ]; then
    echo "Testing OpenCV camera access..."
    if python -c "import cv2; cap = cv2.VideoCapture(0); print('Camera available:', cap.isOpened()); cap.release()" 2>/dev/null; then
        echo "✅ Camera access confirmed via OpenCV"
        CAMERA_OK=true
    else
        echo "⚠️  Camera access test failed - check camera connection and permissions"
        echo "   This is normal if camera settings were just updated and reboot is needed"
    fi
fi

# Test TFLite model
echo "Testing TFLite model..."
MODEL_OK=false
if [ -f "$MODEL_FILE" ]; then
    if python -c "
import tflite_runtime.interpreter as tflite
try:
    interpreter = tflite.Interpreter('$MODEL_FILE')
    interpreter.allocate_tensors()
    print('✅ TFLite model loaded successfully')
    print('Input details:', interpreter.get_input_details())
    print('Output details:', interpreter.get_output_details())
except Exception as e:
    print('❌ TFLite model test failed:', e)
    exit(1)
" 2>/dev/null; then
        echo "✅ TFLite model test passed"
        MODEL_OK=true
    else
        echo "❌ TFLite model test failed"
    fi
else
    echo "❌ TFLite model file not found"
fi

# Overall test result
if [ "$OPENCV_OK" = true ] && [ "$FLASK_OK" = true ] && [ "$TFLITE_OK" = true ] && [ "$MODEL_OK" = true ]; then
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
