#!/bin/bash

# Cat Counter Detection System Restore Script
# This script restores a backup of the system configuration and detection data

echo "=== Cat Counter Detection System Restore ==="
echo "This script will restore your system configuration and detection data from a backup."
echo ""

# Check if backup file is provided
if [ $# -ne 1 ]; then
    echo "Usage: $0 <backup_file.tar.gz>"
    echo "Available backups:"
    ls -1 backups/*.tar.gz 2>/dev/null || echo "No backups found in backups/ directory."
    exit 1
fi

BACKUP_FILE=$1

# Check if backup file exists
if [ ! -f "${BACKUP_FILE}" ]; then
    echo "Error: Backup file ${BACKUP_FILE} not found."
    exit 1
fi

# Create temporary directory for extraction
TEMP_DIR=$(mktemp -d)

echo "Extracting backup to temporary location..."
tar -xzf "${BACKUP_FILE}" -C "${TEMP_DIR}"

# Find the backup directory (should be only one directory)
BACKUP_DIR=$(find "${TEMP_DIR}" -mindepth 1 -maxdepth 1 -type d)

if [ -z "${BACKUP_DIR}" ]; then
    echo "Error: Invalid backup format. Could not find backup directory."
    rm -rf "${TEMP_DIR}"
    exit 1
fi

# Stop the cat detection service if it's running
echo "Stopping cat detection service..."
sudo systemctl stop cat-detection.service 2>/dev/null || true

# Restore configuration
echo "Restoring configuration..."
if [ -f "${BACKUP_DIR}/config.json" ]; then
    cp "${BACKUP_DIR}/config.json" config.json
    echo "Configuration restored."
else
    echo "Warning: Configuration file not found in backup."
fi

# Restore database
echo "Restoring detection database..."
if [ -f "${BACKUP_DIR}/detections.db" ]; then
    # Create data directory if it doesn't exist
    mkdir -p data
    cp "${BACKUP_DIR}/detections.db" data/detections.db
    echo "Database restored."
else
    echo "Warning: Detection database not found in backup."
fi

# Restore images
echo "Restoring detection images..."
if [ -d "${BACKUP_DIR}/images" ] && [ "$(ls -A "${BACKUP_DIR}/images")" ]; then
    mkdir -p data/images
    cp "${BACKUP_DIR}/images/"* data/images/
    IMAGE_COUNT=$(find "${BACKUP_DIR}/images" -type f | wc -l)
    echo "Restored ${IMAGE_COUNT} images."
else
    echo "Warning: No images found in backup."
fi

# Clean up
rm -rf "${TEMP_DIR}"

# Start the cat detection service
echo "Starting cat detection service..."
sudo systemctl start cat-detection.service 2>/dev/null || true

echo ""
echo "=== Restore Complete ==="
echo "Your system has been restored from the backup."
echo ""