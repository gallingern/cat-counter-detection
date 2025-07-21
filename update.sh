#!/bin/bash

# Simple Cat Detection System Update Script
# 
# This script performs quick updates after git pull.
# For full installation, use install.sh instead.

echo "=== Simple Cat Detection System Update ==="

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
else
    echo "❌ Virtual environment not found - please run install.sh for full setup"
    exit 1
fi

# Stop service and processes
echo "🔄 Stopping services and processes..."
sudo systemctl stop cat-detector 2>/dev/null || true
sudo pkill -f "start_detection.py" 2>/dev/null || true
sleep 2

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
sudo tee /etc/systemd/system/cat-detector.service > /dev/null << EOL
[Unit]
Description=Cat Detection Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python $(pwd)/start_detection.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOL

# Start service
echo "🔄 Starting service..."
sudo systemctl daemon-reload
sudo systemctl enable cat-detector 2>/dev/null
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
if sudo journalctl -u cat-detector -n 50 --no-pager | grep -q "Setting camera to native resolution"; then
    echo "✅ New camera code loaded (native resolution set)"
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
