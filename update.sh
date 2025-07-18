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

# Fix any retry_on_error decorator issues in Python files
echo "Fixing retry_on_error decorator issues in Python files..."
find cat_counter_detection -name "*.py" -type f -exec grep -l "retry_on_error" {} \; | while read file; do
    echo "Checking $file for retry_on_error issues..."
    if grep -q "max_attempts" "$file"; then
        echo "Fixing retry_on_error in $file..."
        # Replace max_attempts with max_retries
        sed -i 's/@retry_on_error(max_attempts=/@retry_on_error(max_retries=/g' "$file"
        # Replace delay= with delay_seconds=
        sed -i 's/delay=/delay_seconds=/g' "$file"
        # Replace exceptions= with component_name=
        sed -i 's/exceptions=([^)]*)/component_name="auto_fixed"/g' "$file"
        echo "✓ Fixed $file"
    fi
done

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

# Check if web server is running
echo ""
echo "Checking web server status..."
WEB_PORT=5000
IP_ADDRESS=$(hostname -I | awk '{print $1}')
WEB_URL="http://$IP_ADDRESS:$WEB_PORT"

# Check if port 5000 is listening
if netstat -tuln | grep -q ":$WEB_PORT "; then
    echo "✓ Web server is listening on port $WEB_PORT"
    
    # Try to connect to the web server
    if curl -s --head --fail "$WEB_URL" > /dev/null; then
        echo "✓ Web server is responding to HTTP requests"
    else
        echo "✗ Web server is not responding to HTTP requests"
        echo "  Possible issues:"
        echo "  - The web application might not be properly initialized"
        echo "  - There might be a firewall blocking connections"
    fi
else
    echo "✗ Web server is not listening on port $WEB_PORT"
    echo "  Possible issues:"
    echo "  - The web application might not be starting correctly"
    echo "  - The port might be in use by another application"
    
    # Check logs for errors
    echo ""
    echo "Checking service logs for errors..."
    sudo journalctl -u cat-detection -n 20 --no-pager
fi

# Check if the web app is configured in the code
echo ""
echo "Checking web app configuration..."
if grep -q "app.run" cat_counter_detection/web/app.py 2>/dev/null; then
    echo "✓ Web application is configured in the code"
    grep -n "app.run" cat_counter_detection/web/app.py
else
    echo "✗ Could not find web application configuration"
    echo "  The web interface might not be properly implemented"
fi

echo ""
echo "Update complete! The service has been restarted with the latest changes."
echo "To view the web interface, navigate to: $WEB_URL"
echo ""
echo "If the web interface is not working, try the following:"
echo "1. Check if the service is running: sudo systemctl status cat-detection"
echo "2. Check the logs for errors: sudo journalctl -u cat-detection -n 50"
echo "3. Make sure port 5000 is not blocked by a firewall"
echo "4. Try restarting the service: sudo systemctl restart cat-detection"