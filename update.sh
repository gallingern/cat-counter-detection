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

# Stop service and processes first
echo "🔄 Stopping services and processes..."
sudo pkill -f "start_detection.py" 2>/dev/null || true
sudo pkill -f "python.*cat-counter-detection" 2>/dev/null || true
if systemctl is-active --quiet cat-detection; then
    sudo systemctl stop cat-detection
fi
sleep 2

# Clear Python cache efficiently
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

# Restart service
echo "🔄 Restarting service..."
sudo systemctl daemon-reload
sudo systemctl start cat-detection
sleep 5

# Check service status
if ! systemctl is-active --quiet cat-detection; then
    echo "❌ Service failed to start"
    sudo journalctl -u cat-detection -n 10 --no-pager
    exit 1
fi

# Verify new code is loaded
echo "🔍 Verifying new code..."
sleep 3
if sudo journalctl -u cat-detection -n 50 --no-pager | grep -q "Setting camera to native resolution"; then
    echo "✅ New camera code loaded (native resolution set)"
elif sudo journalctl -u cat-detection -n 50 --no-pager | grep -q "Starting camera capture loop"; then
    echo "✅ New camera code loaded"
elif sudo journalctl -u cat-detection -n 50 --no-pager | grep -q "Failed to read frame from camera"; then
    echo "⚠️  Old code detected - cache clearing may have failed"
else
    echo "ℹ️  Service started"
fi

# Check web server
echo "🌐 Checking web server..."
WEB_PORT=5000
IP_ADDRESS=$(hostname -I | awk '{print $1}')
WEB_URL="http://$IP_ADDRESS:$WEB_PORT"

if curl -s --head --fail "$WEB_URL" > /dev/null 2>&1; then
    echo "✅ Web server running at $WEB_URL"
    echo ""
    echo "=== Update Complete! ==="
    echo "✅ System updated successfully"
    echo "🌐 Web interface available at: $WEB_URL"
else
    echo "❌ Web server not responding"
    echo ""
    echo "=== Update Complete! ==="
    echo "⚠️  Update completed but web server may need attention"
    echo "   Check logs: sudo journalctl -u cat-detection -f"
fi
