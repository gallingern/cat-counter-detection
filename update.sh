#!/bin/bash

# Quick update script for Cat Counter Detection System
# This script only updates the necessary files and restarts the service

echo "=== Cat Counter Detection System Quick Update ==="
echo "This script will update only the necessary files and restart the service."
echo ""

# Initialize status tracking arrays
successful_operations=()
failed_operations=()

# Check if git repository exists
if [ ! -d ".git" ]; then
    echo "Error: This doesn't appear to be a git repository."
    echo "Please run the full install.sh script instead."
    failed_operations+=("Git repository check")
    exit 1
else
    successful_operations+=("Git repository check")
fi

# Pull latest changes
echo "┌─────────────────────────────────────────────┐"
echo "│ Pulling latest changes from git repository  │"
echo "└─────────────────────────────────────────────┘"
git stash &> /dev/null  # Save any local changes
if git pull; then
    successful_operations+=("Git pull")
else
    echo "❌ ERROR: Failed to pull latest changes."
    failed_operations+=("Git pull")
    exit 1
fi

# Update systemd service file
echo "┌─────────────────────────────────────────────┐"
echo "│ Updating systemd service file               │"
echo "└─────────────────────────────────────────────┘"
if sudo tee /etc/systemd/system/cat-detection.service > /dev/null << EOL
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
then
    successful_operations+=("Systemd service file update")
else
    echo "❌ ERROR: Failed to update systemd service file."
    failed_operations+=("Systemd service file update")
fi

# Reload systemd and restart service
echo "┌─────────────────────────────────────────────┐"
echo "│ Reloading systemd and restarting service    │"
echo "└─────────────────────────────────────────────┘"
if sudo systemctl daemon-reload; then
    successful_operations+=("Systemd daemon reload")
else
    echo "❌ ERROR: Failed to reload systemd daemon."
    failed_operations+=("Systemd daemon reload")
fi

if sudo systemctl restart cat-detection; then
    successful_operations+=("Service restart")
else
    echo "❌ ERROR: Failed to restart service."
    failed_operations+=("Service restart")
fi

# Check service status
echo "┌─────────────────────────────────────────────┐"
echo "│ Checking service status                     │"
echo "└─────────────────────────────────────────────┘"
service_status=$(sudo systemctl is-active cat-detection)
if [ "$service_status" = "active" ]; then
    successful_operations+=("Service status check")
else
    failed_operations+=("Service status check")
    echo "❌ Service is not active. Current status: $service_status"
    
    # Check service logs for errors
    echo "Checking service logs for errors..."
    sudo journalctl -u cat-detection -n 20 --no-pager
fi

sudo systemctl status cat-detection --no-pager

# Check if web server is running
echo "┌─────────────────────────────────────────────┐"
echo "│ Checking web server status                  │"
echo "└─────────────────────────────────────────────┘"
WEB_PORT=5000
IP_ADDRESS=$(hostname -I | awk '{print $1}')
WEB_URL="http://$IP_ADDRESS:$WEB_PORT"
web_server_status="failed"

# Check if port 5000 is listening
if netstat -tuln | grep -q ":$WEB_PORT "; then
    echo "✅ Web server is listening on port $WEB_PORT"
    
    # Try to connect to the web server
    if curl -s --head --fail "$WEB_URL" > /dev/null; then
        echo "✅ Web server is responding to HTTP requests"
        successful_operations+=("Web server check")
        web_server_status="success"
    else
        echo -e "\e[31m❌ Web server is not responding to HTTP requests\e[0m"
        echo -e "\e[31m  Possible issues:\e[0m"
        echo -e "\e[31m  - The web application might not be properly initialized\e[0m"
        echo -e "\e[31m  - There might be a firewall blocking connections\e[0m"
        failed_operations+=("Web server HTTP response")
        
        # Run diagnostics
        echo ""
        echo -e "\e[33m=== Web Server Diagnostics ===\e[0m"
        
        # Check if curl can connect with verbose output
        echo -e "\e[33m→ Testing connection with verbose output:\e[0m"
        curl -v "$WEB_URL" 2>&1 | grep -E "^(\*|>|<)" | head -10
        
        # Check if the port is actually in use
        echo -e "\e[33m→ Checking process using port $WEB_PORT:\e[0m"
        sudo lsof -i :$WEB_PORT || echo "No process found using port $WEB_PORT"
    fi
else
    echo -e "\e[31m❌ Web server is not listening on port $WEB_PORT\e[0m"
    echo -e "\e[31m  Possible issues:\e[0m"
    echo -e "\e[31m  - The web application might not be starting correctly\e[0m"
    echo -e "\e[31m  - The port might be in use by another application\e[0m"
    failed_operations+=("Web server port check")
    
    # Run comprehensive diagnostics
    echo ""
    echo -e "\e[33m=== Web Server Diagnostics ===\e[0m"
    
    # Check if the port is in use by another process
    echo -e "\e[33m→ Checking if port $WEB_PORT is in use by another process:\e[0m"
    if sudo lsof -i :$WEB_PORT 2>/dev/null; then
        echo -e "\e[31m  Port $WEB_PORT is already in use by another process!\e[0m"
    else
        echo -e "\e[32m  Port $WEB_PORT is available.\e[0m"
    fi
    
    # Check for web server related errors in the logs
    echo -e "\e[33m→ Checking for web server related errors in logs:\e[0m"
    WEB_ERRORS=$(sudo journalctl -u cat-detection -n 100 | grep -i "web\|flask\|app.run\|port\|import\|error\|exception\|failed" | tail -15)
    if [ -n "$WEB_ERRORS" ]; then
        echo -e "\e[31m  Found potential web server errors:\e[0m"
        echo "$WEB_ERRORS" | while read -r line; do
            # Highlight key error terms
            echo "$line" | grep --color=always -E "error|exception|failed|traceback|import|module|not found|conflict"
        done
    else
        echo -e "\e[33m  No specific web server errors found in recent logs.\e[0m"
        
        # Show last few log entries anyway
        echo -e "\e[33m→ Last 10 log entries from service:\e[0m"
        sudo journalctl -u cat-detection -n 10 --no-pager
    fi
    
    # Check if Flask is installed
    echo -e "\e[33m→ Checking if Flask is installed:\e[0m"
    if source venv/bin/activate && python -c "import flask; print(f'Flask version: {flask.__version__}')" 2>/dev/null; then
        echo -e "\e[32m  Flask is installed correctly.\e[0m"
    else
        echo -e "\e[31m  Flask is not installed or not accessible!\e[0m"
        echo -e "\e[31m  Try running: pip install flask\e[0m"
    fi
    
    # Check if the web app module exists and is importable
    echo -e "\e[33m→ Checking web app module:\e[0m"
    if [ -f "cat_counter_detection/web/app.py" ]; then
        echo -e "\e[32m  Web app module exists at cat_counter_detection/web/app.py\e[0m"
        
        # Check for syntax errors in the web app module
        echo -e "\e[33m→ Checking for syntax errors in web app module:\e[0m"
        if source venv/bin/activate && python -m py_compile cat_counter_detection/web/app.py 2>/dev/null; then
            echo -e "\e[32m  No syntax errors found in web app module.\e[0m"
        else
            echo -e "\e[31m  Syntax errors found in web app module!\e[0m"
            source venv/bin/activate && python -c "import py_compile; py_compile.compile('cat_counter_detection/web/app.py')" 2>&1 | head -5
        fi
    else
        echo -e "\e[31m  Web app module not found at cat_counter_detection/web/app.py!\e[0m"
    fi
fi

# Check if the web app is configured in the code
echo "┌─────────────────────────────────────────────┐"
echo "│ Checking web app configuration              │"
echo "└─────────────────────────────────────────────┘"
if grep -q "app.run" cat_counter_detection/web/app.py 2>/dev/null; then
    echo "✅ Web application is configured in the code"
    grep -n "app.run" cat_counter_detection/web/app.py
    successful_operations+=("Web app configuration check")
else
    echo "❌ Could not find web application configuration"
    echo "  The web interface might not be properly implemented"
    failed_operations+=("Web app configuration check")
fi

# Check for Python syntax errors in key files
echo "┌─────────────────────────────────────────────┐"
echo "│ Checking for syntax errors in key files     │"
echo "└─────────────────────────────────────────────┘"
source venv/bin/activate
syntax_errors=0

for file in cat_counter_detection/services/*.py cat_counter_detection/*.py; do
    if [ -f "$file" ]; then
        if ! python -m py_compile "$file" 2>/dev/null; then
            echo -e "\e[31m❌ Syntax error in $file\e[0m"
            python -c "import py_compile; py_compile.compile('$file')" 2>&1 | head -5
            syntax_errors=$((syntax_errors + 1))
            failed_operations+=("Syntax check: $(basename "$file")")
        fi
    fi
done

if [ $syntax_errors -eq 0 ]; then
    echo "✅ No syntax errors found in key Python files"
    successful_operations+=("Python syntax check")
else
    echo -e "\e[31m❌ Found $syntax_errors files with syntax errors\e[0m"
fi

# Generate summary
echo ""
echo "┌─────────────────────────────────────────────┐"
echo "│ Update Summary                              │"
echo "└─────────────────────────────────────────────┘"

# Print successful operations
echo -e "\n\e[1mSuccessful Operations:\e[0m"
for op in "${successful_operations[@]}"; do
    echo -e "\e[32m✅ $op\e[0m"
done

# Print failed operations
if [ ${#failed_operations[@]} -gt 0 ]; then
    echo -e "\n\e[1mFailed Operations:\e[0m"
    for op in "${failed_operations[@]}"; do
        echo -e "\e[31m❌ $op\e[0m"
    done
    
    echo -e "\n\e[33mTroubleshooting Recommendations:\e[0m"
    if [[ " ${failed_operations[*]} " =~ "Service status check" ]]; then
        echo -e "  - Check service logs: \e[36msudo journalctl -u cat-detection -n 50\e[0m"
        echo -e "  - Try manual restart: \e[36msudo systemctl restart cat-detection\e[0m"
    fi
    
    if [[ " ${failed_operations[*]} " =~ "Web server" ]]; then
        echo -e "  - Check if Flask is installed: \e[36msource venv/bin/activate && pip list | grep Flask\e[0m"
        echo -e "  - Check firewall settings: \e[36msudo ufw status\e[0m"
        echo -e "  - Try accessing web interface from the Pi itself: \e[36mcurl http://localhost:5000\e[0m"
    fi
    
    if [[ " ${failed_operations[*]} " =~ "Syntax check" ]]; then
        echo -e "  - Fix syntax errors in the identified files"
        echo -e "  - Run update script again after fixing errors"
    fi
else
    echo -e "\n\e[32m✅ All operations completed successfully!\e[0m"
fi

echo ""
echo "┌─────────────────────────────────────────────┐"
echo "│ Update complete!                            │"
echo "└─────────────────────────────────────────────┘"
echo "The service has been restarted with the latest changes."
if [ "$web_server_status" = "success" ]; then
    echo -e "\e[32m✅ Web interface is available at: $WEB_URL\e[0m"
else
    echo -e "\e[33mWeb interface should be available at: $WEB_URL (when issues are resolved)\e[0m"
fi