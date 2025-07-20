#!/bin/bash

# Simple Cat Detection System Update Script
# 
# This script performs quick updates after git pull.
# For full installation, use install.sh instead.

echo "=== Simple Cat Detection System Update ==="
echo "This script will update the system and restart the service."
echo ""

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
        echo "❌ Git pull failed"
        echo "   Continuing with service restart..."
    fi
fi

# Check and update dependencies
echo "🔧 Checking dependencies..."
if [ -d "venv" ]; then
    source venv/bin/activate
    if [ $? -ne 0 ]; then
        echo "❌ Failed to activate virtual environment"
        echo "   Recreating virtual environment..."
        rm -rf venv
        python3 -m venv venv
        source venv/bin/activate
    fi
    
    # Check if packages are installed
    if ! python -c "import cv2, flask, numpy" 2>/dev/null; then
        echo "⚠️  Some dependencies missing, installing..."
        pip install opencv-python flask numpy
    else
        echo "✅ All Python dependencies already installed"
    fi
else
    echo "❌ Virtual environment not found"
    echo "   Please run install.sh for full setup"
    exit 1
fi

# Update systemd service if needed
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

# Restart the service
echo "🔄 Restarting service..."
sudo systemctl daemon-reload
if systemctl is-active --quiet cat-detection; then
    echo "Restarting existing service..."
    sudo systemctl restart cat-detection
else
    echo "Starting service..."
    sudo systemctl start cat-detection
fi

# Wait a moment for service to start
sleep 2

# Check service status
echo "🔍 Checking service status..."
if systemctl is-active --quiet cat-detection; then
    echo "✅ Service is running"
else
    echo "❌ Service failed to start"
    echo "   Checking logs..."
    sudo journalctl -u cat-detection -n 10 --no-pager
    exit 1
fi

# Check if web server is running
echo "🌐 Checking web server..."
WEB_PORT=5000
IP_ADDRESS=$(hostname -I | awk '{print $1}')
WEB_URL="http://$IP_ADDRESS:$WEB_PORT"

# Wait a moment for web server to start
sleep 3

# Try to connect to the web server
if curl -s --head --fail "$WEB_URL" > /dev/null 2>&1; then
    echo "✅ Web server is running at $WEB_URL"
    WEB_OK=true
else
    echo "❌ Web server is not responding"
    echo "   Checking service logs..."
    sudo journalctl -u cat-detection -n 20 --no-pager
    WEB_OK=false
fi

echo ""
echo "=== Update Complete! ==="

if [ "$WEB_OK" = true ]; then
    echo "✅ System updated successfully"
    echo "🌐 Web interface available at: $WEB_URL"
else
    echo "⚠️  Update completed but web server may need attention"
    echo "   Check logs: sudo journalctl -u cat-detection -f"
fi