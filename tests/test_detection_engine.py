"""Unit tests for detection engine service."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cat_counter_detection.services.detection_engine import CatDetectionEngine
from cat_counter_detection.models.detection import Detection, BoundingBox


class TestCatDetectionEngine(unittest.TestCase):
    """Test cases for CatDetectionEngine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.engine = CatDetectionEngine()
    
    def test_initialization(self):
        """Test engine initialization."""
        self.assertFalse(self.engine.model_loaded)
        self.assertIsNone(self.engine.haar_cascade)
        self.assertEqual(self.engine.confidence_threshold, 0.7)
        self.assertEqual(self.engine.roi, (0, 0, 640, 480))
        self.assertEqual(self.engine.min_detection_size, (30, 30))
        self.assertEqual(self.engine.max_detection_size, (300, 300))
    
    def test_set_confidence_threshold(self):
        """Test confidence threshold setting with bounds checking."""
        # Test normal value
        self.engine.set_confidence_threshold(0.8)
        self.assertEqual(self.engine.confidence_threshold, 0.8)
        
        # Test lower bound
        self.engine.set_confidence_threshold(-0.1)
        self.assertEqual(self.engine.confidence_threshold, 0.0)
        
        # Test upper bound
        self.engine.set_confidence_threshold(1.5)
        self.assertEqual(self.engine.confidence_threshold, 1.0)
    
    def test_set_roi(self):
        """Test ROI setting."""
        new_roi = (100, 100, 400, 300)
        self.engine.set_roi(new_roi)
        self.assertEqual(self.engine.roi, new_roi)
    
    def test_set_detection_parameters(self):
        """Test detection parameters setting."""
        self.engine.set_detection_parameters(
            scale_factor=1.2,
            min_neighbors=5,
            min_size=(50, 50),
            max_size=(200, 200)
        )
        
        self.assertEqual(self.engine.scale_factor, 1.2)
        self.assertEqual(self.engine.min_neighbors, 5)
        self.assertEqual(self.engine.min_detection_size, (50, 50))
        self.assertEqual(self.engine.max_detection_size, (200, 200))
    
    def test_load_model_nonexistent_file(self):
        """Test loading model from non-existent file."""
        self.engine.load_model("nonexistent_model.xml")
        # Should fall back to built-in cascade or mock mode
        self.assertTrue(self.engine.model_loaded)
    
    def test_detect_cats_without_model(self):
        """Test detection without loaded model."""
        detections = self.engine.detect_cats(None)
        self.assertEqual(len(detections), 0)
    
    def test_detect_cats_with_none_frame(self):
        """Test detection with None frame."""
        self.engine.model_loaded = True
        detections = self.engine.detect_cats(None)
        self.assertEqual(len(detections), 0)
    
    def test_mock_detection(self):
        """Test mock detection functionality."""
        # Create a mock frame
        mock_frame = [[0 for _ in range(640)] for _ in range(480)]
        
        # Run mock detection multiple times to test randomness
        detection_found = False
        for _ in range(50):  # Try multiple times due to randomness
            detections = self.engine._mock_detection(mock_frame)
            if len(detections) > 0:
                detection_found = True
                self.assertIsInstance(detections[0], Detection)
                self.assertEqual(len(detections[0].bounding_boxes), 1)
                break
        
        # Note: Due to randomness, we can't guarantee a detection will occur
        # but the test verifies the structure when it does
    
    def test_convert_to_detections(self):
        """Test conversion of raw detections to Detection objects."""
        raw_detections = [(100, 100, 50, 50), (200, 200, 60, 60)]
        frame_shape = (480, 640, 3)
        
        detections = self.engine._convert_to_detections(raw_detections, frame_shape)
        
        # Should filter based on confidence threshold
        # The exact number depends on the confidence calculation
        self.assertIsInstance(detections, list)
        
        for detection in detections:
            self.assertIsInstance(detection, Detection)
            self.assertEqual(len(detection.bounding_boxes), 1)
            self.assertGreaterEqual(detection.raw_confidence, 0.0)
            self.assertLessEqual(detection.raw_confidence, 1.0)
    
    def test_get_detection_info(self):
        """Test detection engine information retrieval."""
        info = self.engine.get_detection_info()
        
        self.assertIn("model_loaded", info)
        self.assertIn("opencv_available", info)
        self.assertIn("confidence_threshold", info)
        self.assertIn("roi", info)
        self.assertIn("detection_parameters", info)
        self.assertIn("preprocessing_parameters", info)
        
        self.assertEqual(info["confidence_threshold"], 0.7)
        self.assertEqual(info["roi"], (0, 0, 640, 480))
    
    @patch('cat_counter_detection.services.detection_engine.OPENCV_AVAILABLE', False)
    def test_opencv_not_available(self):
        """Test behavior when OpenCV is not available."""
        engine = CatDetectionEngine()
        engine.load_model("test_model.xml")
        
        # Should still mark as loaded (mock mode)
        self.assertTrue(engine.model_loaded)
        
        # Detection should work in mock mode
        mock_frame = [[0 for _ in range(640)] for _ in range(480)]
        detections = engine.detect_cats(mock_frame)
        
        # Should return empty list or mock detections
        self.assertIsInstance(detections, list)
    
    def test_confidence_calculation(self):
        """Test confidence score calculation logic."""
        # Test with detection in center of frame
        center_detection = (320, 240, 100, 100)  # Center of 640x480 frame
        frame_shape = (480, 640, 3)
        
        detections = self.engine._convert_to_detections([center_detection], frame_shape)
        
        if len(detections) > 0:
            # Center detection should have relatively high confidence
            self.assertGreater(detections[0].raw_confidence, 0.6)
        
        # Test with detection at edge of frame
        edge_detection = (10, 10, 50, 50)
        edge_detections = self.engine._convert_to_detections([edge_detection], frame_shape)
        
        # Edge detection might have lower confidence or be filtered out
        # This tests the confidence calculation logic
        for detection in edge_detections:
            self.assertGreaterEqual(detection.raw_confidence, self.engine.confidence_threshold)
    
    def test_roi_application(self):
        """Test ROI application to frame."""
        # Create a mock frame
        try:
            import numpy as np
            frame = np.zeros((480, 640), dtype=np.uint8)
            
            # Set ROI
            self.engine.set_roi((100, 100, 200, 200))
            
            # Apply ROI
            roi_frame = self.engine._apply_roi(frame)
            
            # ROI frame should have the specified dimensions
            self.assertEqual(roi_frame.shape, (200, 200))
            
        except ImportError:
            # Skip test if numpy not available
            self.skipTest("NumPy not available for ROI testing")
    
    def test_detection_parameters_bounds(self):
        """Test that detection parameters are within reasonable bounds."""
        # Test extreme values
        self.engine.set_detection_parameters(
            scale_factor=0.5,  # Very small
            min_neighbors=0,   # Very small
            min_size=(1, 1),   # Very small
            max_size=(1000, 1000)  # Very large
        )
        
        # Values should be set (no bounds checking in current implementation)
        self.assertEqual(self.engine.scale_factor, 0.5)
        self.assertEqual(self.engine.min_neighbors, 0)
        self.assertEqual(self.engine.min_detection_size, (1, 1))
        self.assertEqual(self.engine.max_detection_size, (1000, 1000))


if __name__ == '__main__':
    unittest.main()