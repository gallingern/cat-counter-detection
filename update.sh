#!/bin/bash

# Simple Cat Detection System Update Script
# 
# This script is for quick updates after git pull.
# For full installation, use install.sh instead.
# 
# Differences:
# - install.sh: Full system setup, package installation, service creation
# - update.sh: Git pull, dependency updates, service restart, web testing

echo "=== Simple Cat Detection System Update ==="
echo "This script will update the system and restart the service."
echo ""

# Check if git repository exists
if [ ! -d ".git" ]; then
    echo "⚠️  Warning: This doesn't appear to be a git repository."
    echo "    Updates will be limited to restarting the service."
else
    # Pull latest changes
    echo "📦 Pulling latest changes..."
    if git pull; then
        echo "✅ Git pull successful"
        
        # Reinstall dependencies if needed
        echo "🔧 Checking if dependencies need updating..."
        if [ -d "venv" ]; then
            source venv/bin/activate
            # Quick check if packages are installed
            if ! python -c "import cv2, flask, picamera, numpy" 2>/dev/null; then
                echo "⚠️  Some dependencies missing, installing..."
                pip install picamera opencv-python flask numpy
            else
                echo "✅ All Python dependencies already installed"
            fi
        fi
    else
        echo "❌ Git pull failed"
        echo "   Continuing with service restart..."
    fi
fi

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

# Check service status
echo "🔍 Checking service status..."
sudo systemctl status cat-detection --no-pager

# Check if web server is running
echo "🌐 Checking web server..."
WEB_PORT=5000
IP_ADDRESS=$(hostname -I | awk '{print $1}')
WEB_URL="http://$IP_ADDRESS:$WEB_PORT"

# Try to connect to the web server
if curl -s --head --fail "$WEB_URL" > /dev/null; then
    echo "✅ Web server is running at $WEB_URL"
else
    echo "❌ Web server is not responding"
    echo "   Try checking the logs: sudo journalctl -u cat-detection -n 50"
fi

echo ""
echo "=== Update Complete! ==="