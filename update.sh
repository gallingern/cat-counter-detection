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

# Activate virtual environment
echo "🔧 Activating virtual environment..."
if [ -d "venv" ]; then
    source venv/bin/activate
    if [ $? -ne 0 ]; then
        echo "❌ Failed to activate virtual environment"
        echo "   Recreating virtual environment..."
        rm -rf venv
        python3 -m venv venv
        source venv/bin/activate
    fi
else
    echo "❌ Virtual environment not found"
    echo "   Please run install.sh for full setup"
    exit 1
fi

# Comprehensive Python cache clearing to prevent old code loading
echo "🧹 Clearing Python cache (comprehensive)..."
# Remove all __pycache__ directories recursively
sudo find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
# Remove all .pyc files
sudo find . -name "*.pyc" -delete 2>/dev/null || true
# Remove all .pyo files
sudo find . -name "*.pyo" -delete 2>/dev/null || true
# Remove any remaining cache directories
sudo rm -rf ./__pycache__ 2>/dev/null || true
sudo rm -rf ./venv/__pycache__ 2>/dev/null || true

# Additional aggressive cache clearing (same as manual commands)
echo "🧹 Additional aggressive cache clearing..."
# Check if cached files still exist
if [ -n "$(find . -name "*.pyc" 2>/dev/null)" ]; then
    echo "Found cached .pyc files, removing..."
    sudo find . -name "*.pyc" -delete
fi

# Check if __pycache__ directories exist
if [ -n "$(find . -name "__pycache__" 2>/dev/null)" ]; then
    echo "Found __pycache__ directories, removing..."
    sudo find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null
fi

# Force clear cache manually (same commands as manual fix)
sudo find . -name "*.pyc" -delete
sudo find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Force kill any running Python processes to ensure clean restart
echo "🔄 Force stopping any running processes..."
sudo pkill -f "start_detection.py" 2>/dev/null || true
sudo pkill -f "python.*cat-counter-detection" 2>/dev/null || true
sleep 2

# Verify cache is cleared
echo "🔍 Verifying cache is cleared..."
if [ -d "./__pycache__" ] || [ -n "$(find . -name "*.pyc" 2>/dev/null)" ]; then
    echo "⚠️  Cache still exists, forcing removal..."
    sudo rm -rf ./__pycache__ 2>/dev/null || true
    sudo find . -name "*.pyc" -delete 2>/dev/null || true
    sleep 1
    # Double-check cache is cleared
    if [ -d "./__pycache__" ] || [ -n "$(find . -name "*.pyc" 2>/dev/null)" ]; then
        echo "❌ Cache clearing failed - manual intervention required"
        echo "   Run: sudo find . -name '*.pyc' -delete && sudo find . -name '__pycache__' -exec rm -rf {} +"
        exit 1
    else
        echo "✅ Cache successfully cleared"
    fi
else
    echo "✅ Cache already cleared"
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

# Force stop and restart the service to ensure new code loads
echo "🔄 Restarting service with new code..."
sudo systemctl daemon-reload

# Force stop the service
if systemctl is-active --quiet cat-detection; then
    echo "Stopping existing service..."
    sudo systemctl stop cat-detection
    sleep 1
fi

# Start the service with new code
echo "Starting service with updated code..."
sudo systemctl start cat-detection

# Wait for service to fully start
sleep 3

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

# Verify new code is being used by checking recent logs
echo "🔍 Verifying new code is loaded..."
sleep 5  # Wait longer for service to fully start and log messages
if sudo journalctl -u cat-detection -n 50 --no-pager | grep -q "Starting camera capture loop"; then
    echo "✅ New camera code is loaded and working"
elif sudo journalctl -u cat-detection -n 50 --no-pager | grep -q "Camera native resolution"; then
    echo "✅ New camera code is loaded (using native resolution)"
elif sudo journalctl -u cat-detection -n 50 --no-pager | grep -q "Failed to read frame from camera"; then
    echo "⚠️  Old code detected - cache clearing may have failed"
    echo "   Consider manual cache clearing: sudo find . -name '*.pyc' -delete"
else
    echo "ℹ️  Service started, checking web interface..."
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
