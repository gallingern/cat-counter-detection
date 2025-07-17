"""Tests for the enhanced cat detection engine with MobileNetV2 support."""

import unittest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from cat_counter_detection.services.enhanced_detection_engine import EnhancedCatDetectionEngine
from cat_counter_detection.models.detection import Detection, BoundingBox


class TestEnhancedCatDetectionEngine(unittest.TestCase):
    """Test cases for enhanced cat detection engine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.engine = EnhancedCatDetectionEngine()
        self.test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    def test_initialization(self):
        """Test engine initialization."""
        self.assertFalse(self.engine.primary_model_loaded)
        self.assertFalse(self.engine.fallback_model_loaded)
        self.assertEqual(self.engine.current_model, "none")
        self.assertEqual(self.engine.confidence_threshold, 0.7)
        self.assertEqual(self.engine.roi, (0, 0, 640, 480))
        self.assertIsNotNone(self.engine.opencv_engine)
    
    def test_set_confidence_threshold(self):
        """Test setting confidence threshold."""
        self.engine.set_confidence_threshold(0.8)
        self.assertEqual(self.engine.confidence_threshold, 0.8)
        
        # Test bounds
        self.engine.set_confidence_threshold(-0.1)
        self.assertEqual(self.engine.confidence_threshold, 0.0)
        
        self.engine.set_confidence_threshold(1.5)
        self.assertEqual(self.engine.confidence_threshold, 1.0)
    
    def test_set_roi(self):
        """Test setting region of interest."""
        roi = (100, 100, 400, 300)
        self.engine.set_roi(roi)
        self.assertEqual(self.engine.roi, roi)
    
    @patch('cat_counter_detection.services.enhanced_detection_engine.TFLITE_AVAILABLE', False)
    def test_load_model_no_tflite(self):
        """Test model loading when TensorFlow Lite is not available."""
        with patch.object(self.engine, '_load_fallback_model') as mock_fallback:
            self.engine.load_model("test_model.tflite")
            mock_fallback.assert_called_once()
    
    @patch('cat_counter_detection.services.enhanced_detection_engine.TFLITE_AVAILABLE', True)
    @patch('os.path.exists')
    def test_load_model_file_not_found(self, mock_exists):
        """Test model loading when file doesn't exist."""
        mock_exists.return_value = False
        
        with patch.object(self.engine, '_load_fallback_model') as mock_fallback:
            self.engine.load_model("nonexistent_model.tflite")
            mock_fallback.assert_called_once()
    
    @patch('cat_counter_detection.services.enhanced_detection_engine.TFLITE_AVAILABLE', True)
    @patch('cat_counter_detection.services.enhanced_detection_engine.tflite')
    @patch('os.path.exists')
    def test_load_mobilenet_model_success(self, mock_exists, mock_tflite):
        """Test successful MobileNet model loading."""
        mock_exists.return_value = True
        
        # Mock TensorFlow Lite interpreter
        mock_interpreter = Mock()
        mock_interpreter.get_input_details.return_value = [
            {'shape': np.array([1, 224, 224, 3]), 'dtype': np.float32, 'name': 'input'}
        ]
        mock_interpreter.get_output_details.return_value = [
            {'shape': np.array([1, 10, 4]), 'dtype': np.float32, 'name': 'boxes'},
            {'shape': np.array([1, 10]), 'dtype': np.float32, 'name': 'classes'},
            {'shape': np.array([1, 10]), 'dtype': np.float32, 'name': 'scores'},
            {'shape': np.array([1]), 'dtype': np.float32, 'name': 'num_detections'}
        ]
        
        mock_tflite.Interpreter.return_value = mock_interpreter
        
        self.engine.load_model("test_model.tflite")
        
        self.assertTrue(self.engine.primary_model_loaded)
        self.assertEqual(self.engine.current_model, "mobilenet")
        self.assertEqual(self.engine.input_size, (224, 224))
    
    def test_detect_cats_no_model(self):
        """Test detection when no model is loaded."""
        detections = self.engine.detect_cats(self.test_frame)
        self.assertEqual(len(detections), 0)
    
    @patch('cat_counter_detection.services.enhanced_detection_engine.OPENCV_AVAILABLE', False)
    def test_detect_cats_no_opencv(self):
        """Test detection when OpenCV is not available."""
        self.engine.fallback_model_loaded = True
        self.engine.current_model = "opencv"
        
        detections = self.engine.detect_cats(self.test_frame)
        self.assertEqual(len(detections), 0)
    
    def test_detect_cats_none_frame(self):
        """Test detection with None frame."""
        detections = self.engine.detect_cats(None)
        self.assertEqual(len(detections), 0)
    
    def test_get_current_model(self):
        """Test getting current model."""
        self.assertEqual(self.engine.get_current_model(), "none")
        
        self.engine.current_model = "mobilenet"
        self.assertEqual(self.engine.get_current_model(), "mobilenet")
    
    def test_force_fallback_to_opencv(self):
        """Test forcing fallback to OpenCV."""
        # Without fallback model loaded
        result = self.engine.force_fallback_to_opencv()
        self.assertFalse(result)
        
        # With fallback model loaded
        self.engine.fallback_model_loaded = True
        result = self.engine.force_fallback_to_opencv()
        self.assertTrue(result)
        self.assertEqual(self.engine.current_model, "opencv")
    
    def test_switch_to_mobilenet(self):
        """Test switching to MobileNet model."""
        # Without primary model loaded
        result = self.engine.switch_to_mobilenet()
        self.assertFalse(result)
        
        # With primary model loaded
        self.engine.primary_model_loaded = True
        result = self.engine.switch_to_mobilenet()
        self.assertTrue(result)
        self.assertEqual(self.engine.current_model, "mobilenet")
    
    @patch('cat_counter_detection.services.enhanced_detection_engine.OPENCV_AVAILABLE', True)
    def test_preprocess_frame_for_mobilenet(self):
        """Test frame preprocessing for MobileNet."""
        # Mock cv2
        with patch('cat_counter_detection.services.enhanced_detection_engine.cv2') as mock_cv2:
            mock_cv2.resize.return_value = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
            mock_cv2.cvtColor.return_value = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
            
            self.engine.input_size = (224, 224)
            self.engine.quantized_model = False
            
            result = self.engine._preprocess_frame_for_mobilenet(self.test_frame)
            
            self.assertEqual(result.shape, (1, 224, 224, 3))
            self.assertEqual(result.dtype, np.float32)
            mock_cv2.resize.assert_called_once()
    
    def test_filter_cat_detections(self):
        """Test filtering detections for cats only."""
        # Mock detections with different class IDs
        mock_detections = [
            {'bbox': (100, 100, 50, 50), 'confidence': 0.8, 'class_id': 16},  # Cat
            {'bbox': (200, 200, 60, 60), 'confidence': 0.9, 'class_id': 17},  # Dog
            {'bbox': (300, 300, 40, 40), 'confidence': 0.7, 'class_id': 16},  # Cat
        ]
        
        cat_detections = self.engine._filter_cat_detections(mock_detections)
        
        self.assertEqual(len(cat_detections), 2)
        for detection in cat_detections:
            self.assertIsInstance(detection, Detection)
            self.assertEqual(len(detection.bounding_boxes), 1)
    
    def test_apply_roi_filtering(self):
        """Test ROI filtering of detections."""
        # Set ROI
        self.engine.set_roi((100, 100, 200, 200))
        
        # Create test detections
        bbox1 = BoundingBox(x=150, y=150, width=50, height=50, confidence=0.8)  # Inside ROI
        bbox2 = BoundingBox(x=50, y=50, width=30, height=30, confidence=0.9)    # Outside ROI
        
        detection1 = Detection(
            timestamp=None,
            bounding_boxes=[bbox1],
            frame_width=640,
            frame_height=480,
            raw_confidence=0.8
        )
        
        detection2 = Detection(
            timestamp=None,
            bounding_boxes=[bbox2],
            frame_width=640,
            frame_height=480,
            raw_confidence=0.9
        )
        
        detections = [detection1, detection2]
        filtered = self.engine._apply_roi_filtering(detections)
        
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].bounding_boxes[0].x, 150)
    
    @patch('cat_counter_detection.services.enhanced_detection_engine.OPENCV_AVAILABLE', True)
    def test_apply_nms(self):
        """Test non-maximum suppression."""
        with patch('cat_counter_detection.services.enhanced_detection_engine.cv2') as mock_cv2:
            # Mock NMS to return indices [0, 2] (keeping first and third detection)
            mock_cv2.dnn.NMSBoxes.return_value = np.array([[0], [2]])
            
            mock_detections = [
                {'bbox': (100, 100, 50, 50), 'confidence': 0.8},
                {'bbox': (110, 110, 50, 50), 'confidence': 0.7},  # Overlapping, should be removed
                {'bbox': (200, 200, 50, 50), 'confidence': 0.9},
            ]
            
            result = self.engine._apply_nms(mock_detections)
            
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]['bbox'], (100, 100, 50, 50))
            self.assertEqual(result[1]['bbox'], (200, 200, 50, 50))
    
    def test_optimize_for_raspberry_pi_zero_w(self):
        """Test Raspberry Pi Zero W optimizations."""
        result = self.engine.optimize_for_raspberry_pi_zero_w()
        
        self.assertTrue(result["success"])
        self.assertTrue(self.engine.arm_optimized)
        self.assertEqual(self.engine.input_size, (192, 192))
        self.assertGreaterEqual(self.engine.confidence_threshold, 0.75)
        self.assertEqual(self.engine.nms_threshold, 0.5)
        self.assertEqual(self.engine.max_detections, 5)
        self.assertIn("optimizations_applied", result)
    
    def test_get_model_info(self):
        """Test getting model information."""
        info = self.engine.get_model_info()
        
        required_keys = [
            "primary_model_loaded", "fallback_model_loaded", "current_model",
            "tflite_available", "opencv_available", "quantized_model",
            "arm_optimized", "confidence_threshold", "roi", "input_size"
        ]
        
        for key in required_keys:
            self.assertIn(key, info)
        
        self.assertEqual(info["current_model"], "none")
        self.assertEqual(info["confidence_threshold"], 0.7)
        self.assertEqual(info["roi"], (0, 0, 640, 480))
    
    def test_set_opencv_model_path(self):
        """Test setting OpenCV model path."""
        with patch.object(self.engine.opencv_engine, 'load_model') as mock_load:
            self.engine.set_opencv_model_path("test_opencv_model.xml")
            mock_load.assert_called_once_with("test_opencv_model.xml")


class TestModelIntegration(unittest.TestCase):
    """Integration tests for model loading and detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.engine = EnhancedCatDetectionEngine()
    
    def test_fallback_mechanism(self):
        """Test that fallback mechanism works correctly."""
        # Try to load a non-existent MobileNet model
        self.engine.load_model("nonexistent_model.tflite")
        
        # Should fall back to OpenCV
        self.assertTrue(self.engine.fallback_model_loaded or self.engine.primary_model_loaded)
        self.assertIn(self.engine.current_model, ["opencv", "mobilenet", "none"])
    
    @patch('cat_counter_detection.services.enhanced_detection_engine.TFLITE_AVAILABLE', True)
    @patch('cat_counter_detection.services.enhanced_detection_engine.OPENCV_AVAILABLE', True)
    def test_model_switching(self):
        """Test switching between models."""
        # Set up both models as loaded
        self.engine.primary_model_loaded = True
        self.engine.fallback_model_loaded = True
        self.engine.current_model = "mobilenet"
        
        # Switch to OpenCV
        result = self.engine.force_fallback_to_opencv()
        self.assertTrue(result)
        self.assertEqual(self.engine.current_model, "opencv")
        
        # Switch back to MobileNet
        result = self.engine.switch_to_mobilenet()
        self.assertTrue(result)
        self.assertEqual(self.engine.current_model, "mobilenet")


if __name__ == '__main__':
    unittest.main()