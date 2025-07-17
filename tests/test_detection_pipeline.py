"""Integration tests for detection pipeline."""

import unittest
import tempfile
import shutil
import time
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cat_counter_detection.detection_pipeline import DetectionPipeline
from cat_counter_detection.config_manager import ConfigManager
from cat_counter_detection.models.config import SystemConfig


class TestDetectionPipeline(unittest.TestCase):
    """Test cases for DetectionPipeline integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        
        # Create test configuration
        config_path = os.path.join(self.test_dir, "test_config.json")
        self.config_manager = ConfigManager(config_path)
        
        # Initialize pipeline
        self.pipeline = DetectionPipeline(self.config_manager)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if self.pipeline.running:
            self.pipeline.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_pipeline_initialization(self):
        """Test pipeline initialization."""
        self.assertIsNotNone(self.pipeline.config_manager)
        self.assertIsNotNone(self.pipeline.frame_capture)
        self.assertIsNotNone(self.pipeline.detection_engine)
        self.assertIsNotNone(self.pipeline.detection_validator)
        self.assertIsNotNone(self.pipeline.storage_service)
        self.assertIsNotNone(self.pipeline.notification_service)
        
        self.assertFalse(self.pipeline.running)
        self.assertEqual(self.pipeline.detection_count, 0)
        self.assertEqual(self.pipeline.error_count, 0)
    
    def test_pipeline_start_stop(self):
        """Test pipeline start and stop functionality."""
        # Start pipeline
        success = self.pipeline.start()
        self.assertTrue(success)
        self.assertTrue(self.pipeline.running)
        self.assertIsNotNone(self.pipeline.pipeline_thread)
        
        # Brief wait to ensure thread is running
        time.sleep(0.1)
        self.assertTrue(self.pipeline.pipeline_thread.is_alive())
        
        # Stop pipeline
        self.pipeline.stop()
        self.assertFalse(self.pipeline.running)
    
    def test_pipeline_start_already_running(self):
        """Test starting pipeline when already running."""
        # Start pipeline
        success1 = self.pipeline.start()
        self.assertTrue(success1)
        
        # Try to start again
        success2 = self.pipeline.start()
        self.assertFalse(success2)  # Should return False
        
        self.pipeline.stop()
    
    def test_monitoring_schedule(self):
        """Test monitoring schedule functionality."""
        # Test with monitoring enabled (default)
        self.assertTrue(self.pipeline._is_monitoring_active())
        
        # Test with monitoring disabled
        self.pipeline.config.monitoring_enabled = False
        self.assertFalse(self.pipeline._is_monitoring_active())
        
        # Test with time-based monitoring
        self.pipeline.config.monitoring_enabled = True
        self.pipeline.config.monitoring_start_hour = 9
        self.pipeline.config.monitoring_end_hour = 17
        
        # The result depends on current time, but should not raise an error
        result = self.pipeline._is_monitoring_active()
        self.assertIsInstance(result, bool)
    
    def test_configuration_update(self):
        """Test configuration updates."""
        original_threshold = self.pipeline.config.confidence_threshold
        
        # Update configuration
        self.pipeline.update_configuration(confidence_threshold=0.8)
        
        # Check that configuration was updated
        self.assertEqual(self.pipeline.config.confidence_threshold, 0.8)
        self.assertNotEqual(self.pipeline.config.confidence_threshold, original_threshold)
        
        # Check that services were updated
        self.assertEqual(self.pipeline.detection_engine.confidence_threshold, 0.8)
        self.assertEqual(self.pipeline.detection_validator.confidence_threshold, 0.8)
    
    def test_get_status(self):
        """Test status retrieval."""
        status = self.pipeline.get_status()
        
        self.assertIn("running", status)
        self.assertIn("monitoring_active", status)
        self.assertIn("uptime_seconds", status)
        self.assertIn("frame_count", status)
        self.assertIn("current_fps", status)
        self.assertIn("detection_count", status)
        self.assertIn("error_count", status)
        self.assertIn("last_detection", status)
        self.assertIn("services", status)
        
        # Check service status
        services = status["services"]
        self.assertIn("frame_capture", services)
        self.assertIn("detection_engine", services)
        self.assertIn("detection_validator", services)
        self.assertIn("storage_service", services)
        self.assertIn("notification_service", services)
        
        # Initial values
        self.assertFalse(status["running"])
        self.assertEqual(status["frame_count"], 0)
        self.assertEqual(status["detection_count"], 0)
        self.assertEqual(status["error_count"], 0)
    
    def test_trigger_test_detection(self):
        """Test triggering a test detection."""
        initial_count = self.pipeline.detection_count
        
        success = self.pipeline.trigger_test_detection()
        self.assertTrue(success)
        
        # Detection count should not change (test detection is handled separately)
        # but the method should execute without error
    
    def test_cleanup_old_data(self):
        """Test data cleanup functionality."""
        # Should not raise an error
        self.pipeline.cleanup_old_data()
    
    def test_get_recent_detections(self):
        """Test getting recent detections."""
        detections = self.pipeline.get_recent_detections(limit=5)
        self.assertIsInstance(detections, list)
        # Should be empty initially or contain test data from other tests
        self.assertGreaterEqual(len(detections), 0)
    
    def test_performance_metrics_update(self):
        """Test performance metrics updating."""
        initial_frame_count = self.pipeline.frame_count
        
        # Simulate frame processing
        self.pipeline._update_performance_metrics()
        
        self.assertEqual(self.pipeline.frame_count, initial_frame_count + 1)
    
    def test_notification_message_creation(self):
        """Test notification message creation."""
        from cat_counter_detection.models.detection import ValidDetection, BoundingBox
        
        # Create test detection
        from datetime import datetime
        bbox = BoundingBox(x=100, y=100, width=50, height=50, confidence=0.8)
        detection = ValidDetection(
            timestamp=datetime.now(),
            bounding_boxes=[bbox],
            frame_width=640,
            frame_height=480,
            raw_confidence=0.8,
            cat_count=2,
            is_on_counter=True,
            validated_confidence=0.85
        )
        
        # Test notification sending (should not raise error)
        try:
            self.pipeline._send_notifications(detection, "/test/image.jpg")
        except Exception as e:
            self.fail(f"Notification sending raised an exception: {e}")
    
    def test_frame_processing_with_no_detections(self):
        """Test frame processing when no cats are detected."""
        mock_frame = [[0 for _ in range(640)] for _ in range(480)]
        
        # Mock detection engine to return no detections
        original_method = self.pipeline.detection_engine.detect_cats
        self.pipeline.detection_engine.detect_cats = lambda frame: []
        
        initial_count = self.pipeline.detection_count
        
        # Process frame
        self.pipeline._process_frame(mock_frame)
        
        # Detection count should not change
        self.assertEqual(self.pipeline.detection_count, initial_count)
        
        # Restore original method
        self.pipeline.detection_engine.detect_cats = original_method
    
    def test_frame_processing_with_invalid_detections(self):
        """Test frame processing when detections don't pass validation."""
        mock_frame = [[0 for _ in range(640)] for _ in range(480)]
        
        # Mock detection engine to return detections that won't pass validation
        from cat_counter_detection.models.detection import Detection, BoundingBox
        
        # Create detection with very low confidence
        bbox = BoundingBox(x=100, y=100, width=50, height=50, confidence=0.3)
        mock_detection = Detection(
            timestamp=time.time(),
            bounding_boxes=[bbox],
            frame_width=640,
            frame_height=480,
            raw_confidence=0.3  # Below threshold
        )
        
        original_method = self.pipeline.detection_engine.detect_cats
        self.pipeline.detection_engine.detect_cats = lambda frame: [mock_detection]
        
        initial_count = self.pipeline.detection_count
        
        # Process frame
        self.pipeline._process_frame(mock_frame)
        
        # Detection count should not change (detection should be filtered out)
        self.assertEqual(self.pipeline.detection_count, initial_count)
        
        # Restore original method
        self.pipeline.detection_engine.detect_cats = original_method
    
    def test_error_handling_in_frame_processing(self):
        """Test error handling during frame processing."""
        mock_frame = [[0 for _ in range(640)] for _ in range(480)]
        
        # Mock detection engine to raise an error
        original_method = self.pipeline.detection_engine.detect_cats
        self.pipeline.detection_engine.detect_cats = lambda frame: (_ for _ in ()).throw(Exception("Test error"))
        
        initial_error_count = self.pipeline.error_count
        
        # Process frame (should handle error gracefully)
        self.pipeline._process_frame(mock_frame)
        
        # Error count should increase
        self.assertEqual(self.pipeline.error_count, initial_error_count + 1)
        
        # Restore original method
        self.pipeline.detection_engine.detect_cats = original_method
    
    def test_model_loading(self):
        """Test detection model loading."""
        # Should not raise an error even if model files don't exist
        try:
            self.pipeline._load_detection_model()
        except Exception as e:
            self.fail(f"Model loading raised an exception: {e}")
        
        # Detection engine should be loaded (in mock mode if no real model)
        self.assertTrue(self.pipeline.detection_engine.model_loaded)
    
    def test_roi_configuration(self):
        """Test ROI configuration updates."""
        new_roi = (50, 50, 300, 200)
        
        self.pipeline.update_configuration(detection_roi=new_roi)
        
        self.assertEqual(self.pipeline.config.detection_roi, new_roi)
        self.assertEqual(self.pipeline.detection_engine.roi, new_roi)
        self.assertEqual(self.pipeline.detection_validator.counter_roi, new_roi)
    
    def test_fps_configuration(self):
        """Test FPS configuration updates."""
        new_fps = 2.0
        
        self.pipeline.update_configuration(target_fps=new_fps)
        
        self.assertEqual(self.pipeline.config.target_fps, new_fps)
        self.assertEqual(self.pipeline.frame_capture.framerate, new_fps)


if __name__ == '__main__':
    unittest.main()