#!/bin/bash

# Cat Counter Detection System Update Script
# This script updates the system software and dependencies

echo "=== Cat Counter Detection System Update ==="
echo "This script will update your system software and dependencies."
echo ""

# Create backup before updating
echo "Creating backup before update..."
./backup.sh

# Stop the cat detection service
echo "Stopping cat detection service..."
sudo systemctl stop cat-detection.service 2>/dev/null || true

# Update system packages
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Update Python dependencies
echo "Updating Python dependencies..."
pip3 install --upgrade -r requirements.txt

# Check for git repository
if [ -d ".git" ]; then
    echo "Checking for software updates..."
    
    # Stash any local changes
    git stash
    
    # Get the current version
    CURRENT_VERSION=$(git describe --tags --always)
    
    # Pull latest changes
    git pull
    
    # Get the new version
    NEW_VERSION=$(git describe --tags --always)
    
    if [ "$CURRENT_VERSION" != "$NEW_VERSION" ]; then
        echo "Updated from version ${CURRENT_VERSION} to ${NEW_VERSION}"
    else
        echo "Already at the latest version: ${CURRENT_VERSION}"
    fi
else
    echo "Not a git repository. Skipping software update check."
fi

# Restart the cat detection service
echo "Starting cat detection service..."
sudo systemctl start cat-detection.service

echo ""
echo "=== Update Complete ==="
echo "Your system has been updated to the latest version."
echo ""