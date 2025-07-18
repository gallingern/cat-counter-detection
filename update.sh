#!/bin/bash

# Quick update script for Cat Counter Detection System
# This script only updates the necessary files and restarts the service

echo "=== Cat Counter Detection System Quick Update ==="
echo "This script will update only the necessary files and restart the service."
echo ""

# Check if git repository exists
if [ ! -d ".git" ]; then
    echo "Error: This doesn't appear to be a git repository."
    echo "Please run the full install.sh script instead."
    exit 1
fi

# Pull latest changes
echo "Pulling latest changes from git repository..."
git stash &> /dev/null  # Save any local changes
git pull || {
    echo "Error: Failed to pull latest changes."
    exit 1
}

# Update systemd service file
echo "Updating systemd service file..."
sudo tee /etc/systemd/system/cat-detection.service > /dev/null << EOL
[Unit]
Description=Cat Counter Detection Service
After=network.target

[Service]
ExecStart=$(pwd)/venv/bin/python $(pwd)/start_detection.py
WorkingDirectory=$(pwd)
StandardOutput=inherit
StandardError=inherit
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
EOL

# Reload systemd and restart service
echo "Reloading systemd and restarting service..."
sudo systemctl daemon-reload
sudo systemctl restart cat-detection

# Check service status
echo "Checking service status..."
sudo systemctl status cat-detection --no-pager

echo ""
echo "Update complete! The service has been restarted with the latest changes."
echo "To view the web interface, navigate to: http://$(hostname -I | awk '{print $1}'):5000"