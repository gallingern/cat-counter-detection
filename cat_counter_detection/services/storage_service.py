"""Storage service implementation for images and detection history."""

import logging
import os
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Optional, Any
from ..models.detection import ValidDetection, DetectionRecord, BoundingBox
from ..models.config import StorageStats
from .interfaces import StorageServiceInterface
from ..utils import ensure_directory_exists, cleanup_old_files, get_file_size_mb
from .error_handler import global_error_handler, ErrorSeverity, with_error_handling, retry_on_error
from ..logging_config import get_logger, log_performance

# Handle image processing imports gracefully
try:
    from PIL import Image
    import numpy as np
    IMAGE_PROCESSING_AVAILABLE = True
except ImportError:
    IMAGE_PROCESSING_AVAILABLE = False
    Image = None
    np = None

logger = get_logger("storage_service")


class StorageService(StorageServiceInterface):
    """Storage service for managing detection images and history."""
    
    def __init__(self, 
                 storage_dir: str = "data",
                 images_dir: str = "data/images",
                 database_path: str = "data/detections.db",
                 image_quality: int = 85,
                 max_storage_days: int = 30):
        """
        Initialize storage service.
        
        Args:
            storage_dir: Base directory for all storage
            images_dir: Directory for storing detection images
            database_path: Path to SQLite database file
            image_quality: JPEG compression quality (1-100)
            max_storage_days: Maximum days to keep data
        """
        self.storage_dir = storage_dir
        self.images_dir = images_dir
        self.database_path = database_path
        self.image_quality = max(1, min(100, image_quality))
        self.max_storage_days = max_storage_days
        
        # Error tracking
        self.storage_errors = 0
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5
        self.degraded_mode = False
        
        # Register with error handler
        global_error_handler.register_component("storage_service", max_recovery_attempts=3)
        global_error_handler.register_recovery_strategy("DatabaseError", self._recover_database_error)
        global_error_handler.register_recovery_strategy("PermissionError", self._recover_permission_error)
        global_error_handler.register_recovery_strategy("IOError", self._recover_io_error)
        
        # Initialize storage
        self._initialize_storage()
    
    def save_detection(self, detection: ValidDetection, image: Any) -> str:
        """Save detection and return image path."""
        try:
            # Generate unique filename
            timestamp_str = detection.timestamp.strftime("%Y%m%d_%H%M%S_%f")[:-3]
            image_filename = f"cat_detection_{timestamp_str}.jpg"
            image_path = os.path.join(self.images_dir, image_filename)
            
            # Save image
            self._save_image(image, image_path)
            
            # Save detection record to database
            detection_record = DetectionRecord(
                timestamp=detection.timestamp,
                cat_count=detection.cat_count,
                confidence_score=detection.validated_confidence,
                image_path=image_path,
                bounding_boxes=detection.bounding_boxes
            )
            
            self._save_detection_record(detection_record)
            
            logger.info(f"Saved detection with {detection.cat_count} cats to {image_path}")
            return image_path
            
        except Exception as e:
            logger.error(f"Failed to save detection: {e}")
            raise
    
    def get_detection_history(self, start_date: datetime, end_date: datetime) -> List[DetectionRecord]:
        """Get detection history for date range."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT timestamp, cat_count, confidence_score, image_path, bounding_boxes
                    FROM detections
                    WHERE timestamp BETWEEN ? AND ?
                    ORDER BY timestamp DESC
                """, (start_date.isoformat(), end_date.isoformat()))
                
                records = []
                for row in cursor.fetchall():
                    timestamp_str, cat_count, confidence_score, image_path, bounding_boxes_json = row
                    
                    # Parse timestamp
                    timestamp = datetime.fromisoformat(timestamp_str)
                    
                    # Parse bounding boxes
                    bounding_boxes = self._deserialize_bounding_boxes(bounding_boxes_json)
                    
                    record = DetectionRecord(
                        timestamp=timestamp,
                        cat_count=cat_count,
                        confidence_score=confidence_score,
                        image_path=image_path,
                        bounding_boxes=bounding_boxes
                    )
                    records.append(record)
                
                logger.debug(f"Retrieved {len(records)} detection records from {start_date} to {end_date}")
                return records
                
        except Exception as e:
            logger.error(f"Failed to get detection history: {e}")
            return []
    
    def cleanup_old_data(self) -> None:
        """Clean up old detection data."""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.max_storage_days)
            
            # Clean up database records
            deleted_records = self._cleanup_old_database_records(cutoff_date)
            
            # Clean up old image files
            deleted_images = cleanup_old_files(self.images_dir, self.max_storage_days)
            
            logger.info(f"Cleanup completed: {deleted_records} database records, "
                       f"{deleted_images} image files deleted")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
    
    def get_storage_usage(self) -> StorageStats:
        """Get storage usage statistics."""
        try:
            # Calculate directory sizes
            total_size = self._get_directory_size(self.storage_dir)
            images_size = self._get_directory_size(self.images_dir)
            
            # Get detection count and date range
            detection_count, oldest_date, newest_date = self._get_detection_stats()
            
            # Get available disk space
            if hasattr(os, 'statvfs'):  # Unix-like systems
                statvfs = os.statvfs(self.storage_dir)
                available_space = statvfs.f_bavail * statvfs.f_frsize / (1024 * 1024)  # MB
                total_space = statvfs.f_blocks * statvfs.f_frsize / (1024 * 1024)  # MB
            else:  # Windows or fallback
                import shutil
                total_space, used_space, available_space = shutil.disk_usage(self.storage_dir)
                total_space = total_space / (1024 * 1024)  # Convert to MB
                available_space = available_space / (1024 * 1024)  # Convert to MB
            
            return StorageStats(
                total_space_mb=total_space,
                used_space_mb=total_size,
                available_space_mb=available_space,
                detection_count=detection_count,
                oldest_detection=oldest_date,
                newest_detection=newest_date
            )
            
        except Exception as e:
            logger.error(f"Failed to get storage usage: {e}")
            return StorageStats(
                total_space_mb=0.0,
                used_space_mb=0.0,
                available_space_mb=0.0,
                detection_count=0,
                oldest_detection="N/A",
                newest_detection="N/A"
            )
    
    def _initialize_storage(self) -> None:
        """Initialize storage directories and database."""
        # Create directories
        ensure_directory_exists(self.storage_dir)
        ensure_directory_exists(self.images_dir)
        
        # Initialize database
        self._initialize_database()
        
        logger.info(f"Storage initialized: {self.storage_dir}")
    
    def _initialize_database(self) -> None:
        """Initialize SQLite database with detection table."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS detections (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        cat_count INTEGER NOT NULL,
                        confidence_score REAL NOT NULL,
                        image_path TEXT NOT NULL,
                        bounding_boxes TEXT NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create index for faster queries
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp 
                    ON detections(timestamp)
                """)
                
                conn.commit()
                logger.debug("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _save_image(self, image: Any, image_path: str) -> None:
        """Save image to disk with compression."""
        try:
            if not IMAGE_PROCESSING_AVAILABLE:
                # Mock save for development
                with open(image_path, 'w') as f:
                    f.write("Mock image data")
                return
            
            # Convert numpy array to PIL Image if needed
            if hasattr(image, 'shape'):  # numpy array
                if len(image.shape) == 3:
                    # RGB image
                    pil_image = Image.fromarray(image.astype('uint8'), 'RGB')
                else:
                    # Grayscale image
                    pil_image = Image.fromarray(image.astype('uint8'), 'L')
            else:
                # Assume it's already a PIL Image or compatible
                pil_image = image
            
            # Save with JPEG compression
            pil_image.save(image_path, 'JPEG', quality=self.image_quality, optimize=True)
            
        except Exception as e:
            logger.error(f"Failed to save image {image_path}: {e}")
            # Create a placeholder file so the database record isn't broken
            with open(image_path, 'w') as f:
                f.write(f"Image save failed: {e}")
    
    def _save_detection_record(self, record: DetectionRecord) -> None:
        """Save detection record to database."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Serialize bounding boxes
                bounding_boxes_json = self._serialize_bounding_boxes(record.bounding_boxes)
                
                cursor.execute("""
                    INSERT INTO detections 
                    (timestamp, cat_count, confidence_score, image_path, bounding_boxes)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    record.timestamp.isoformat(),
                    record.cat_count,
                    record.confidence_score,
                    record.image_path,
                    bounding_boxes_json
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save detection record: {e}")
            raise
    
    def _serialize_bounding_boxes(self, bounding_boxes: List[BoundingBox]) -> str:
        """Serialize bounding boxes to JSON string."""
        boxes_data = []
        for bbox in bounding_boxes:
            boxes_data.append({
                'x': bbox.x,
                'y': bbox.y,
                'width': bbox.width,
                'height': bbox.height,
                'confidence': bbox.confidence
            })
        return json.dumps(boxes_data)
    
    def _deserialize_bounding_boxes(self, json_str: str) -> List[BoundingBox]:
        """Deserialize bounding boxes from JSON string."""
        try:
            boxes_data = json.loads(json_str)
            bounding_boxes = []
            
            for box_data in boxes_data:
                bbox = BoundingBox(
                    x=box_data['x'],
                    y=box_data['y'],
                    width=box_data['width'],
                    height=box_data['height'],
                    confidence=box_data['confidence']
                )
                bounding_boxes.append(bbox)
            
            return bounding_boxes
            
        except Exception as e:
            logger.error(f"Failed to deserialize bounding boxes: {e}")
            return []
    
    def _cleanup_old_database_records(self, cutoff_date: datetime) -> int:
        """Clean up old database records and return count of deleted records."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Get image paths of records to be deleted for cleanup
                cursor.execute("""
                    SELECT image_path FROM detections 
                    WHERE timestamp < ?
                """, (cutoff_date.isoformat(),))
                
                old_image_paths = [row[0] for row in cursor.fetchall()]
                
                # Delete old records
                cursor.execute("""
                    DELETE FROM detections 
                    WHERE timestamp < ?
                """, (cutoff_date.isoformat(),))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                # Clean up associated image files
                for image_path in old_image_paths:
                    try:
                        if os.path.exists(image_path):
                            os.remove(image_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete image {image_path}: {e}")
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup old database records: {e}")
            return 0
    
    def _get_directory_size(self, directory: str) -> float:
        """Get total size of directory in MB."""
        if not os.path.exists(directory):
            return 0.0
        
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except (OSError, IOError):
                    pass  # Skip files that can't be accessed
        
        return total_size / (1024 * 1024)  # Convert to MB
    
    def _get_detection_stats(self) -> tuple[int, str, str]:
        """Get detection statistics: count, oldest date, newest date."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Get count
                cursor.execute("SELECT COUNT(*) FROM detections")
                count = cursor.fetchone()[0]
                
                if count == 0:
                    return 0, "N/A", "N/A"
                
                # Get oldest and newest dates
                cursor.execute("""
                    SELECT MIN(timestamp), MAX(timestamp) FROM detections
                """)
                oldest, newest = cursor.fetchone()
                
                return count, oldest or "N/A", newest or "N/A"
                
        except Exception as e:
            logger.error(f"Failed to get detection stats: {e}")
            return 0, "N/A", "N/A"
    
    def get_recent_detections(self, limit: int = 10) -> List[DetectionRecord]:
        """Get most recent detections."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)  # Last week
        
        all_records = self.get_detection_history(start_date, end_date)
        return all_records[:limit]
    
    def _recover_database_error(self, error_record) -> bool:
        """Recover from database errors."""
        logger.info("Attempting database error recovery")
        
        try:
            # Try to reinitialize database
            self._initialize_database()
            
            # Test database connection
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM detections")
                cursor.fetchone()
            
            logger.info("Database error recovery successful")
            self.consecutive_failures = 0
            self.degraded_mode = False
            return True
            
        except Exception as e:
            logger.error(f"Database error recovery failed: {e}")
            self.consecutive_failures += 1
            
            if self.consecutive_failures >= self.max_consecutive_failures:
                logger.critical("Maximum database failures reached - enabling degraded mode")
                self.degraded_mode = True
                global_error_handler.trigger_graceful_degradation("Storage database failures")
            
            return False
    
    def _recover_permission_error(self, error_record) -> bool:
        """Recover from permission errors."""
        logger.info("Attempting permission error recovery")
        
        try:
            # Try to create directories with proper permissions
            os.makedirs(self.storage_dir, mode=0o755, exist_ok=True)
            os.makedirs(self.images_dir, mode=0o755, exist_ok=True)
            
            # Test write access
            test_file = os.path.join(self.storage_dir, "test_write.tmp")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            
            logger.info("Permission error recovery successful")
            self.consecutive_failures = 0
            return True
            
        except Exception as e:
            logger.error(f"Permission error recovery failed: {e}")
            self.degraded_mode = True
            global_error_handler.trigger_graceful_degradation("Storage permission errors")
            return False
    
    def _recover_io_error(self, error_record) -> bool:
        """Recover from I/O errors."""
        logger.info("Attempting I/O error recovery")
        
        try:
            # Check disk space
            if hasattr(os, 'statvfs'):
                statvfs = os.statvfs(self.storage_dir)
                available_space = statvfs.f_bavail * statvfs.f_frsize / (1024 * 1024)  # MB
                
                if available_space < 100:  # Less than 100MB
                    logger.warning("Low disk space detected - triggering cleanup")
                    self.cleanup_old_data()
            
            # Test basic I/O operations
            test_file = os.path.join(self.storage_dir, "io_test.tmp")
            with open(test_file, 'w') as f:
                f.write("I/O test")
            
            with open(test_file, 'r') as f:
                content = f.read()
            
            os.remove(test_file)
            
            if content == "I/O test":
                logger.info("I/O error recovery successful")
                self.consecutive_failures = 0
                return True
            else:
                raise IOError("I/O test failed")
                
        except Exception as e:
            logger.error(f"I/O error recovery failed: {e}")
            self.degraded_mode = True
            return False
    
    @with_error_handling("storage_service", ErrorSeverity.HIGH)
    @retry_on_error(max_retries=3, delay_seconds=1.0, component_name="storage_service")
    def save_detection(self, detection: ValidDetection, image: Any) -> str:
        """Save detection and return image path with comprehensive error handling."""
        start_time = datetime.now()
        
        try:
            if self.degraded_mode:
                logger.warning("Storage service in degraded mode - skipping save")
                return ""
            
            # Generate unique filename
            timestamp_str = detection.timestamp.strftime("%Y%m%d_%H%M%S_%f")[:-3]
            image_filename = f"cat_detection_{timestamp_str}.jpg"
            image_path = os.path.join(self.images_dir, image_filename)
            
            # Save image
            self._save_image(image, image_path)
            
            # Save detection record to database
            detection_record = DetectionRecord(
                timestamp=detection.timestamp,
                cat_count=detection.cat_count,
                confidence_score=detection.validated_confidence,
                image_path=image_path,
                bounding_boxes=detection.bounding_boxes
            )
            
            self._save_detection_record(detection_record)
            
            # Log performance
            save_time = (datetime.now() - start_time).total_seconds()
            log_performance("Detection saved", {
                "cat_count": detection.cat_count,
                "save_time_ms": save_time * 1000,
                "image_path": image_path,
                "degraded_mode": self.degraded_mode
            })
            
            # Reset error counters on success
            if self.consecutive_failures > 0:
                logger.info("Storage service recovered from failures")
                self.consecutive_failures = 0
                self.storage_errors = 0
            
            logger.info(f"Saved detection with {detection.cat_count} cats to {image_path}")
            return image_path
            
        except Exception as e:
            self.storage_errors += 1
            self.consecutive_failures += 1
            
            # Handle error through error handler
            severity = ErrorSeverity.CRITICAL if self.consecutive_failures > 3 else ErrorSeverity.HIGH
            global_error_handler.handle_error("storage_service", e, severity)
            
            # Return empty string on error
            return ""
    
    @with_error_handling("storage_service", ErrorSeverity.MEDIUM)
    def get_detection_history(self, start_date: datetime, end_date: datetime) -> List[DetectionRecord]:
        """Get detection history for date range with error handling."""
        try:
            if self.degraded_mode:
                logger.warning("Storage service in degraded mode - returning empty history")
                return []
            
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT timestamp, cat_count, confidence_score, image_path, bounding_boxes
                    FROM detections
                    WHERE timestamp BETWEEN ? AND ?
                    ORDER BY timestamp DESC
                """, (start_date.isoformat(), end_date.isoformat()))
                
                records = []
                for row in cursor.fetchall():
                    timestamp_str, cat_count, confidence_score, image_path, bounding_boxes_json = row
                    
                    # Parse timestamp
                    timestamp = datetime.fromisoformat(timestamp_str)
                    
                    # Parse bounding boxes
                    bounding_boxes = self._deserialize_bounding_boxes(bounding_boxes_json)
                    
                    record = DetectionRecord(
                        timestamp=timestamp,
                        cat_count=cat_count,
                        confidence_score=confidence_score,
                        image_path=image_path,
                        bounding_boxes=bounding_boxes
                    )
                    records.append(record)
                
                logger.debug(f"Retrieved {len(records)} detection records from {start_date} to {end_date}")
                return records
                
        except Exception as e:
            # Handle error through error handler
            global_error_handler.handle_error("storage_service", e, ErrorSeverity.MEDIUM)
            return []
    
    @with_error_handling("storage_service", ErrorSeverity.LOW)
    def cleanup_old_data(self) -> None:
        """Clean up old detection data with error handling."""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.max_storage_days)
            
            # Clean up database records
            deleted_records = self._cleanup_old_database_records(cutoff_date)
            
            # Clean up old image files
            deleted_images = cleanup_old_files(self.images_dir, self.max_storage_days)
            
            log_performance("Storage cleanup completed", {
                "deleted_records": deleted_records,
                "deleted_images": deleted_images,
                "cutoff_date": cutoff_date.isoformat()
            })
            
            logger.info(f"Cleanup completed: {deleted_records} database records, "
                       f"{deleted_images} image files deleted")
            
        except Exception as e:
            global_error_handler.handle_error("storage_service", e, ErrorSeverity.LOW)
    
    def get_storage_info(self) -> dict:
        """Get storage service information."""
        return {
            "storage_dir": self.storage_dir,
            "images_dir": self.images_dir,
            "database_path": self.database_path,
            "image_quality": self.image_quality,
            "max_storage_days": self.max_storage_days,
            "image_processing_available": IMAGE_PROCESSING_AVAILABLE,
            "database_exists": os.path.exists(self.database_path),
            "images_dir_exists": os.path.exists(self.images_dir),
            "error_stats": {
                "storage_errors": self.storage_errors,
                "consecutive_failures": self.consecutive_failures,
                "degraded_mode": self.degraded_mode
            }
        }