#!/bin/bash

# Simple Cat Detection System Update Script

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
    git pull
fi

# Restart the service
echo "🔄 Restarting service..."
sudo systemctl restart cat-detection

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