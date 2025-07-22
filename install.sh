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

# ... (existing dependency installation and Python venv setup) ...

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

# Disable legacy firmware camera stack
sudo sed -i 's/^start_x=1/#&/' "$CONFIG_FILE" || true
sudo sed -i 's/^dtoverlay=imx219/#&/' "$CONFIG_FILE" || true
sudo sed -i 's/^disable_fw_kms_setup=1/#&/' "$CONFIG_FILE" || true

# Add VC4 full-KMS driver
if ! grep -q "^dtoverlay=vc4-kms-v3d" "$CONFIG_FILE"; then
    sudo bash -c "echo 'dtoverlay=vc4-kms-v3d' >> $CONFIG_FILE"
    echo "Added dtoverlay=vc4-kms-v3d"
    CAMERA_CHANGES=true
fi

# Ensure firmware auto-detect remains enabled
if ! grep -q "^camera_auto_detect=1" "$CONFIG_FILE"; then
    sudo bash -c "echo 'camera_auto_detect=1' >> $CONFIG_FILE"
    echo "Added camera_auto_detect=1"
    CAMERA_CHANGES=true
fi

# Enable I²C bus for camera probing
if ! grep -q "^dtparam=i2c_arm=on" "$CONFIG_FILE"; then
    sudo bash -c "echo 'dtparam=i2c_arm=on' >> $CONFIG_FILE"
    echo "Added dtparam=i2c_arm=on"
    CAMERA_CHANGES=true
fi

# Add specific overlay for Camera Module v2 (IMX219)
if ! grep -q "^dtoverlay=imx219" "$CONFIG_FILE"; then
    sudo bash -c "echo 'dtoverlay=imx219' >> $CONFIG_FILE"
    echo "Added dtoverlay=imx219 for Camera Module v2"
    CAMERA_CHANGES=true
fi

# Allocate sufficient GPU RAM
if ! grep -q "^gpu_mem=128" "$CONFIG_FILE"; then
    sudo bash -c "echo 'gpu_mem=128' >> $CONFIG_FILE"
    echo "Added gpu_mem=128"
    CAMERA_CHANGES=true
fi

# Create udev rules for firmware & DMA-heap access
sudo tee /etc/udev/rules.d/99-vcio.rules > /dev/null <<EOF
KERNEL=="vcio", MODE="0666"
EOF
sudo tee /etc/udev/rules.d/99-dma_heap.rules > /dev/null <<EOF
SUBSYSTEM=="dma_heap", GROUP="video", MODE="0660"
EOF
# Add 'pi' user to 'video' group for DMA and firmware access
tty=$(tty)
sudo usermod -aG video pi

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

if [ "$CAMERA_CHANGES" = true ]; then
    echo "⚠️  Camera configuration updated; a reboot will be required."
    REBOOT_REQUIRED=true
fi

# ... (existing service creation and startup logic) ...

echo "The cat detection system is now running."

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