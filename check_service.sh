#!/bin/bash

# Simple Cat Detector Service Status Checker
# This script helps debug service issues and ensure single-instance operation

echo "=== Cat Detector Service Status Check ==="
echo ""

# Check systemd service status
echo "📋 Systemd Service Status:"
if systemctl is-active --quiet cat-detector; then
    echo "✅ Service is ACTIVE"
    systemctl status cat-detector --no-pager -l
else
    echo "❌ Service is INACTIVE"
    systemctl status cat-detector --no-pager -l
fi

echo ""
echo "🔍 Process Check:"
# Check for running processes
PROCESSES=$(pgrep -f "start_detection.py" 2>/dev/null || echo "")
if [ -n "$PROCESSES" ]; then
    echo "✅ Found running processes:"
    ps aux | grep "start_detection.py" | grep -v grep
else
    echo "❌ No start_detection.py processes found"
fi

echo ""
echo "📁 PID File Check:"
# Check PID files
if [ -f "/tmp/cat-detector.pid" ]; then
    PID_CONTENT=$(cat /tmp/cat-detector.pid 2>/dev/null || echo "EMPTY")
    if [ -n "$PID_CONTENT" ] && [ "$PID_CONTENT" != "EMPTY" ]; then
        echo "✅ PID file exists: /tmp/cat-detector.pid (PID: $PID_CONTENT)"
        # Check if PID is actually running
        if kill -0 "$PID_CONTENT" 2>/dev/null; then
            echo "✅ PID $PID_CONTENT is running"
        else
            echo "❌ PID $PID_CONTENT is not running (stale PID file)"
        fi
    else
        echo "❌ PID file is empty: /tmp/cat-detector.pid"
    fi
else
    echo "ℹ️  No PID file found: /tmp/cat-detector.pid"
fi

echo ""
echo "🌐 Port Check:"
# Check if port 5000 is in use
if netstat -tlnp 2>/dev/null | grep -q ":5000 "; then
    echo "✅ Port 5000 is in use:"
    netstat -tlnp 2>/dev/null | grep ":5000 "
else
    echo "❌ Port 5000 is not in use"
fi

echo ""
echo "📊 Recent Logs:"
# Show recent service logs
echo "Last 10 lines of service logs:"
journalctl -u cat-detector -n 10 --no-pager

echo ""
echo "🔧 Quick Fixes:"
echo "If you see issues, try these commands:"
echo "  sudo systemctl stop cat-detector"
echo "  sudo rm -f /tmp/cat-detector.pid"
echo "  sudo systemctl start cat-detector"
echo "  sudo journalctl -u cat-detector -f" 