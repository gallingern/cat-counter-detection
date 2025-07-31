#!/bin/bash

# Simple Cat Detector System Update Script
# 
# This script performs quick updates after git pull.
# For full installation, use install.sh instead.

echo "=== Simple Cat Detector System Update ==="

# Check if git repository exists
if [ ! -d ".git" ]; then
    echo "⚠️  Warning: This doesn't appear to be a git repository."
    echo "    Updates will be limited to restarting the service."
    GIT_AVAILABLE=false
else
    GIT_AVAILABLE=true
fi

# Pull latest changes if git is available
if [ "$GIT_AVAILABLE" = true ]; then
    echo "📦 Pulling latest changes..."
    if git pull; then
        echo "✅ Git pull successful"
    else
        echo "❌ Git pull failed - continuing with service restart..."
    fi
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
if [ -d "venv" ]; then
    source venv/bin/activate
    if [ $? -ne 0 ]; then
        echo "❌ Failed to activate virtual environment - recreating..."
        rm -rf venv
        python3 -m venv venv
        source venv/bin/activate
    fi
    pip install --upgrade tflite-runtime
else
    echo "❌ Virtual environment not found - please run install.sh for full setup"
    exit 1
fi

# Stop service and processes - GRACEFUL FIRST, THEN AGGRESSIVE
echo "🔄 Stopping services and processes..."
# Try graceful stop first
sudo systemctl stop cat-detector 2>/dev/null || true
sleep 3

# Check if service is still running and force kill if needed
if systemctl is-active --quiet cat-detector; then
    echo "Service still running, forcing stop..."
    sudo systemctl kill cat-detector 2>/dev/null || true
    sleep 2
fi

# Kill any remaining processes by name (aggressive cleanup)
echo "Cleaning up any remaining processes..."
sudo pkill -f "start_detection.py" 2>/dev/null || true
sudo pkill -f "python.*start_detection" 2>/dev/null || true
sudo pkill -f "libcamera-vid" 2>/dev/null || true
sudo pkill -f "cat-detector" 2>/dev/null || true

# Clean up PID files
echo "🧹 Cleaning up PID files..."
sudo rm -f /tmp/cat-detector.pid 2>/dev/null || true
sudo rm -f /tmp/cat-detection.pid 2>/dev/null || true

sleep 3

# Clear Python cache
echo "🧹 Clearing Python cache..."
sudo find . -name "*.pyc" -delete 2>/dev/null || true
sudo find . -name "*.pyo" -delete 2>/dev/null || true
sudo find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Verify cache is cleared
if [ -d "./__pycache__" ] || [ -n "$(find . -name "*.pyc" 2>/dev/null)" ]; then
    echo "❌ Cache clearing failed - manual intervention required"
    echo "   Run: sudo find . -name '*.pyc' -delete && sudo find . -name '__pycache__' -exec rm -rf {} +"
    exit 1
else
    echo "✅ Cache cleared successfully"
fi

# Update systemd service
echo "🔧 Updating systemd service..."
if [ -f "cat-detector.service" ]; then
    # Update the service file with correct paths
    sed "s|/home/pi/cat-detector|$(pwd)|g" cat-detector.service | sudo tee /etc/systemd/system/cat-detector.service > /dev/null
    echo "✅ Service file updated from cat-detector.service"
else
    echo "❌ cat-detector.service file not found!"
    exit 1
fi

# Start service
echo "🔄 Starting service..."
sudo systemctl daemon-reload
sudo systemctl enable cat-detector 2>/dev/null

# Ensure no PID file exists before starting
sudo rm -f /tmp/cat-detector.pid 2>/dev/null || true

# Start the service
sudo systemctl start cat-detector

# Wait for service to start and check status
echo "⏳ Waiting for service to start..."
sleep 5

if ! systemctl is-active --quiet cat-detector; then
    echo "❌ Service failed to start"
    sudo journalctl -u cat-detector -n 10 --no-pager
    exit 1
fi

# Verify new code is loaded
echo "🔍 Verifying new code..."
sleep 3
if sudo journalctl -u cat-detector -n 50 --no-pager | grep -q "resolution (320, 240), framerate 2.0"; then
    echo "✅ New camera code loaded (responsive settings)"
elif sudo journalctl -u cat-detector -n 50 --no-pager | grep -q "Starting camera capture loop"; then
    echo "✅ New camera code loaded"
elif sudo journalctl -u cat-detector -n 50 --no-pager | grep -q "Failed to read frame from camera"; then
    echo "⚠️  Camera issues detected - check logs"
else
    echo "ℹ️  Service started"
fi

# Print completion message
echo ""
echo "=== Update Complete! ==="
echo "Check logs: sudo journalctl -u cat-detector -f"
