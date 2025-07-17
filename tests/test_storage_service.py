"""Unit tests for storage service."""

import unittest
import tempfile
import shutil
import os
import sqlite3
from datetime import datetime, timedelta
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cat_counter_detection.services.storage_service import StorageService
from cat_counter_detection.models.detection import ValidDetection, BoundingBox, DetectionRecord


class TestStorageService(unittest.TestCase):
    """Test cases for StorageService."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.storage_dir = os.path.join(self.test_dir, "storage")
        self.images_dir = os.path.join(self.test_dir, "storage", "images")
        self.database_path = os.path.join(self.test_dir, "storage", "test.db")
        
        self.service = StorageService(
            storage_dir=self.storage_dir,
            images_dir=self.images_dir,
            database_path=self.database_path,
            image_quality=85,
            max_storage_days=30
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_test_detection(self) -> ValidDetection:
        """Create a test ValidDetection for testing."""
        bbox = BoundingBox(x=100, y=100, width=50, height=50, confidence=0.8)
        
        return ValidDetection(
            timestamp=datetime.now(),
            bounding_boxes=[bbox],
            frame_width=640,
            frame_height=480,
            raw_confidence=0.8,
            cat_count=1,
            is_on_counter=True,
            validated_confidence=0.85
        )
    
    def create_mock_image(self):
        """Create a mock image for testing."""
        # Return a simple mock image representation
        return [[0 for _ in range(100)] for _ in range(100)]
    
    def test_initialization(self):
        """Test service initialization."""
        self.assertTrue(os.path.exists(self.storage_dir))
        self.assertTrue(os.path.exists(self.images_dir))
        self.assertTrue(os.path.exists(self.database_path))
        
        # Check database table creation
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='detections'
            """)
            self.assertIsNotNone(cursor.fetchone())
    
    def test_save_detection(self):
        """Test saving detection with image."""
        detection = self.create_test_detection()
        mock_image = self.create_mock_image()
        
        image_path = self.service.save_detection(detection, mock_image)
        
        # Check that image file was created
        self.assertTrue(os.path.exists(image_path))
        self.assertTrue(image_path.endswith('.jpg'))
        
        # Check that database record was created
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM detections")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 1)
    
    def test_get_detection_history(self):
        """Test retrieving detection history."""
        # Save multiple detections
        detections = []
        for i in range(3):
            detection = self.create_test_detection()
            detection.timestamp = datetime.now() - timedelta(hours=i)
            detection.cat_count = i + 1
            mock_image = self.create_mock_image()
            
            self.service.save_detection(detection, mock_image)
            detections.append(detection)
        
        # Retrieve history
        end_date = datetime.now() + timedelta(hours=1)
        start_date = datetime.now() - timedelta(days=1)
        
        history = self.service.get_detection_history(start_date, end_date)
        
        self.assertEqual(len(history), 3)
        
        # Check that records are sorted by timestamp (newest first)
        for i in range(len(history) - 1):
            self.assertGreaterEqual(history[i].timestamp, history[i + 1].timestamp)
        
        # Check record content
        for record in history:
            self.assertIsInstance(record, DetectionRecord)
            self.assertGreater(record.cat_count, 0)
            self.assertGreater(record.confidence_score, 0)
            self.assertTrue(os.path.exists(record.image_path))
    
    def test_bounding_box_serialization(self):
        """Test bounding box serialization and deserialization."""
        bbox1 = BoundingBox(x=10, y=20, width=30, height=40, confidence=0.9)
        bbox2 = BoundingBox(x=50, y=60, width=70, height=80, confidence=0.7)
        
        bboxes = [bbox1, bbox2]
        
        # Serialize
        json_str = self.service._serialize_bounding_boxes(bboxes)
        self.assertIsInstance(json_str, str)
        
        # Deserialize
        deserialized_bboxes = self.service._deserialize_bounding_boxes(json_str)
        
        self.assertEqual(len(deserialized_bboxes), 2)
        
        # Check first bounding box
        self.assertEqual(deserialized_bboxes[0].x, 10)
        self.assertEqual(deserialized_bboxes[0].y, 20)
        self.assertEqual(deserialized_bboxes[0].width, 30)
        self.assertEqual(deserialized_bboxes[0].height, 40)
        self.assertEqual(deserialized_bboxes[0].confidence, 0.9)
        
        # Check second bounding box
        self.assertEqual(deserialized_bboxes[1].x, 50)
        self.assertEqual(deserialized_bboxes[1].y, 60)
        self.assertEqual(deserialized_bboxes[1].width, 70)
        self.assertEqual(deserialized_bboxes[1].height, 80)
        self.assertEqual(deserialized_bboxes[1].confidence, 0.7)
    
    def test_cleanup_old_data(self):
        """Test cleanup of old data."""
        # Create old detection
        old_detection = self.create_test_detection()
        old_detection.timestamp = datetime.now() - timedelta(days=35)  # Older than max_storage_days
        
        # Create recent detection
        recent_detection = self.create_test_detection()
        recent_detection.timestamp = datetime.now() - timedelta(days=5)
        
        mock_image = self.create_mock_image()
        
        # Save both detections
        old_image_path = self.service.save_detection(old_detection, mock_image)
        recent_image_path = self.service.save_detection(recent_detection, mock_image)
        
        # Verify both exist
        self.assertTrue(os.path.exists(old_image_path))
        self.assertTrue(os.path.exists(recent_image_path))
        
        # Run cleanup
        self.service.cleanup_old_data()
        
        # Check that old data was removed and recent data remains
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM detections")
            count = cursor.fetchone()[0]
            # Should have 1 record (the recent one)
            self.assertEqual(count, 1)
    
    def test_get_storage_usage(self):
        """Test storage usage statistics."""
        # Save a few detections to generate some data
        for i in range(3):
            detection = self.create_test_detection()
            mock_image = self.create_mock_image()
            self.service.save_detection(detection, mock_image)
        
        stats = self.service.get_storage_usage()
        
        self.assertIsInstance(stats.total_space_mb, float)
        self.assertIsInstance(stats.used_space_mb, float)
        self.assertIsInstance(stats.available_space_mb, float)
        self.assertEqual(stats.detection_count, 3)
        self.assertNotEqual(stats.oldest_detection, "N/A")
        self.assertNotEqual(stats.newest_detection, "N/A")
        
        # Used space should be greater than 0
        self.assertGreater(stats.used_space_mb, 0)
    
    def test_get_recent_detections(self):
        """Test getting recent detections."""
        # Save multiple detections
        for i in range(5):
            detection = self.create_test_detection()
            detection.timestamp = datetime.now() - timedelta(hours=i)
            mock_image = self.create_mock_image()
            self.service.save_detection(detection, mock_image)
        
        # Get recent detections with limit
        recent = self.service.get_recent_detections(limit=3)
        
        self.assertEqual(len(recent), 3)
        
        # Should be sorted by timestamp (newest first)
        for i in range(len(recent) - 1):
            self.assertGreaterEqual(recent[i].timestamp, recent[i + 1].timestamp)
    
    def test_get_storage_info(self):
        """Test storage service information retrieval."""
        info = self.service.get_storage_info()
        
        self.assertIn("storage_dir", info)
        self.assertIn("images_dir", info)
        self.assertIn("database_path", info)
        self.assertIn("image_quality", info)
        self.assertIn("max_storage_days", info)
        self.assertIn("image_processing_available", info)
        self.assertIn("database_exists", info)
        self.assertIn("images_dir_exists", info)
        
        self.assertEqual(info["storage_dir"], self.storage_dir)
        self.assertEqual(info["image_quality"], 85)
        self.assertEqual(info["max_storage_days"], 30)
        self.assertTrue(info["database_exists"])
        self.assertTrue(info["images_dir_exists"])
    
    def test_directory_size_calculation(self):
        """Test directory size calculation."""
        # Create some files
        test_file1 = os.path.join(self.images_dir, "test1.txt")
        test_file2 = os.path.join(self.images_dir, "test2.txt")
        
        with open(test_file1, 'w') as f:
            f.write("x" * 1000)  # 1KB
        
        with open(test_file2, 'w') as f:
            f.write("x" * 2000)  # 2KB
        
        size_mb = self.service._get_directory_size(self.images_dir)
        
        # Should be approximately 3KB = 0.003MB
        self.assertGreater(size_mb, 0.002)
        self.assertLess(size_mb, 0.01)
    
    def test_empty_detection_history(self):
        """Test getting detection history when no records exist."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        
        history = self.service.get_detection_history(start_date, end_date)
        
        self.assertEqual(len(history), 0)
        self.assertIsInstance(history, list)
    
    def test_detection_stats_empty_database(self):
        """Test detection statistics with empty database."""
        count, oldest, newest = self.service._get_detection_stats()
        
        self.assertEqual(count, 0)
        self.assertEqual(oldest, "N/A")
        self.assertEqual(newest, "N/A")


if __name__ == '__main__':
    unittest.main()