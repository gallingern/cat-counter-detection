#!/bin/bash

# Cat Counter Detection System Backup Script
# This script creates a backup of the system configuration and detection data

echo "=== Cat Counter Detection System Backup ==="
echo "This script will create a backup of your system configuration and detection data."
echo ""

# Set backup directory
BACKUP_DIR="backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="cat_detection_backup_${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Create backup subdirectory
mkdir -p "${BACKUP_PATH}"

echo "Creating backup in ${BACKUP_PATH}..."

# Backup configuration
echo "Backing up configuration..."
cp config.json "${BACKUP_PATH}/config.json"

# Backup database
echo "Backing up detection database..."
if [ -f "data/detections.db" ]; then
    # Create a copy of the database to avoid locking issues
    sqlite3 data/detections.db ".backup '${BACKUP_PATH}/detections.db'"
else
    echo "Warning: Detection database not found."
fi

# Backup recent images (last 7 days)
echo "Backing up recent detection images..."
if [ -d "data/images" ]; then
    mkdir -p "${BACKUP_PATH}/images"
    # Find images from the last 7 days
    find data/images -type f -name "*.jpg" -mtime -7 -exec cp {} "${BACKUP_PATH}/images/" \;
    IMAGE_COUNT=$(find "${BACKUP_PATH}/images" -type f | wc -l)
    echo "Backed up ${IMAGE_COUNT} recent images."
else
    echo "Warning: Images directory not found."
fi

# Create archive
echo "Creating compressed archive..."
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" -C "${BACKUP_DIR}" "${BACKUP_NAME}"

# Remove temporary directory
rm -rf "${BACKUP_PATH}"

echo ""
echo "=== Backup Complete ==="
echo "Backup saved to: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo "To restore this backup, use the restore.sh script."
echo ""