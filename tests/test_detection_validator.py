"""Unit tests for detection validator service."""

import unittest
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cat_counter_detection.services.detection_validator import DetectionValidator
from cat_counter_detection.models.detection import Detection, BoundingBox, ValidDetection


class TestDetectionValidator(unittest.TestCase):
    """Test cases for DetectionValidator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = DetectionValidator(
            confidence_threshold=0.7,
            min_detection_size=100,
            counter_roi=(100, 100, 400, 300),
            temporal_consistency_frames=2
        )
    
    def create_test_detection(self, 
                            confidence: float = 0.8,
                            bbox_x: int = 200,
                            bbox_y: int = 200,
                            bbox_size: int = 150) -> Detection:
        """Create a test detection for testing."""
        bbox = BoundingBox(
            x=bbox_x,
            y=bbox_y,
            width=bbox_size,
            height=bbox_size,
            confidence=confidence
        )
        
        return Detection(
            timestamp=datetime.now(),
            bounding_boxes=[bbox],
            frame_width=640,
            frame_height=480,
            raw_confidence=confidence
        )
    
    def test_initialization(self):
        """Test validator initialization."""
        self.assertEqual(self.validator.confidence_threshold, 0.7)
        self.assertEqual(self.validator.min_detection_size, 100)
        self.assertEqual(self.validator.counter_roi, (100, 100, 400, 300))
        self.assertEqual(self.validator.temporal_consistency_frames, 2)
    
    def test_confidence_filter(self):
        """Test confidence threshold filtering."""
        # High confidence detection should pass
        high_conf_detection = self.create_test_detection(confidence=0.8)
        self.assertTrue(self.validator._passes_confidence_filter(high_conf_detection))
        
        # Low confidence detection should fail
        low_conf_detection = self.create_test_detection(confidence=0.5)
        self.assertFalse(self.validator._passes_confidence_filter(low_conf_detection))
        
        # Exact threshold should pass
        exact_conf_detection = self.create_test_detection(confidence=0.7)
        self.assertTrue(self.validator._passes_confidence_filter(exact_conf_detection))
    
    def test_size_filter(self):
        """Test minimum size filtering."""
        # Large detection should pass
        large_detection = self.create_test_detection(bbox_size=150)
        self.assertTrue(self.validator._passes_size_filter(large_detection))
        
        # Small detection should fail (5x5 = 25 pixels < 100)
        small_detection = self.create_test_detection(bbox_size=5)
        self.assertFalse(self.validator._passes_size_filter(small_detection))
        
        # Exact minimum size should pass
        min_size_detection = self.create_test_detection(bbox_size=10)  # 10x10 = 100 pixels
        self.assertTrue(self.validator._passes_size_filter(min_size_detection))
    
    def test_position_filter(self):
        """Test counter position filtering."""
        # Detection in counter area should pass
        counter_detection = self.create_test_detection(bbox_x=200, bbox_y=200)
        self.assertTrue(self.validator._passes_position_filter(counter_detection))
        self.assertTrue(self.validator.is_on_counter(counter_detection))
        
        # Detection outside counter area should fail (center at 25, 25 is outside ROI)
        outside_detection = self.create_test_detection(bbox_x=0, bbox_y=0, bbox_size=50)
        self.assertFalse(self.validator._passes_position_filter(outside_detection))
        self.assertFalse(self.validator.is_on_counter(outside_detection))
    
    def test_iou_calculation(self):
        """Test Intersection over Union calculation."""
        bbox1 = BoundingBox(x=100, y=100, width=100, height=100, confidence=0.8)
        bbox2 = BoundingBox(x=150, y=150, width=100, height=100, confidence=0.8)
        
        iou = self.validator._calculate_iou(bbox1, bbox2)
        
        # Expected IoU for 50% overlap: intersection=2500, union=17500, IoU≈0.14
        self.assertGreater(iou, 0.1)
        self.assertLess(iou, 0.2)
        
        # Test identical boxes (IoU should be 1.0)
        iou_identical = self.validator._calculate_iou(bbox1, bbox1)
        self.assertAlmostEqual(iou_identical, 1.0, places=2)
        
        # Test non-overlapping boxes (IoU should be 0.0)
        bbox3 = BoundingBox(x=300, y=300, width=100, height=100, confidence=0.8)
        iou_no_overlap = self.validator._calculate_iou(bbox1, bbox3)
        self.assertEqual(iou_no_overlap, 0.0)
    
    def test_detection_similarity(self):
        """Test detection similarity comparison."""
        detection1 = self.create_test_detection(bbox_x=200, bbox_y=200)
        detection2 = self.create_test_detection(bbox_x=220, bbox_y=220)  # Slightly moved
        detection3 = self.create_test_detection(bbox_x=400, bbox_y=400)  # Far away
        
        # Similar detections should be considered similar
        self.assertTrue(self.validator._detections_are_similar(detection1, detection2))
        
        # Distant detections should not be similar
        self.assertFalse(self.validator._detections_are_similar(detection1, detection3))
    
    def test_validate_detections_basic(self):
        """Test basic detection validation."""
        # Create valid detection
        valid_detection = self.create_test_detection(
            confidence=0.8,
            bbox_x=200,
            bbox_y=200,
            bbox_size=150
        )
        
        # Create invalid detection (low confidence)
        invalid_detection = self.create_test_detection(
            confidence=0.5,
            bbox_x=200,
            bbox_y=200,
            bbox_size=150
        )
        
        detections = [valid_detection, invalid_detection]
        validated = self.validator.validate_detections(detections)
        
        # Only one detection should pass validation (temporal consistency disabled for this test)
        self.validator.temporal_consistency_frames = 1
        validated = self.validator.validate_detections(detections)
        self.assertEqual(len(validated), 1)
        self.assertIsInstance(validated[0], ValidDetection)
    
    def test_count_cats(self):
        """Test cat counting functionality."""
        # Create multiple valid detections
        detection1 = ValidDetection(
            timestamp=datetime.now(),
            bounding_boxes=[BoundingBox(x=200, y=200, width=100, height=100, confidence=0.8)],
            frame_width=640,
            frame_height=480,
            raw_confidence=0.8,
            cat_count=1,
            is_on_counter=True,
            validated_confidence=0.85
        )
        
        detection2 = ValidDetection(
            timestamp=datetime.now(),
            bounding_boxes=[BoundingBox(x=400, y=300, width=100, height=100, confidence=0.9)],
            frame_width=640,
            frame_height=480,
            raw_confidence=0.9,
            cat_count=1,
            is_on_counter=True,
            validated_confidence=0.95
        )
        
        detections = [detection1, detection2]
        cat_count = self.validator.count_cats(detections)
        
        # Should count 2 cats (non-overlapping detections)
        self.assertEqual(cat_count, 2)
    
    def test_non_maximum_suppression(self):
        """Test non-maximum suppression for overlapping detections."""
        # Create overlapping detections
        detection1 = ValidDetection(
            timestamp=datetime.now(),
            bounding_boxes=[BoundingBox(x=200, y=200, width=100, height=100, confidence=0.9)],
            frame_width=640,
            frame_height=480,
            raw_confidence=0.9,
            cat_count=1,
            is_on_counter=True,
            validated_confidence=0.95
        )
        
        detection2 = ValidDetection(
            timestamp=datetime.now(),
            bounding_boxes=[BoundingBox(x=220, y=220, width=100, height=100, confidence=0.8)],
            frame_width=640,
            frame_height=480,
            raw_confidence=0.8,
            cat_count=1,
            is_on_counter=True,
            validated_confidence=0.85
        )
        
        detections = [detection1, detection2]
        unique_detections = self.validator._apply_non_maximum_suppression(detections)
        
        # Should keep only the higher confidence detection
        self.assertEqual(len(unique_detections), 1)
        self.assertEqual(unique_detections[0].validated_confidence, 0.95)
    
    def test_set_confidence_threshold(self):
        """Test confidence threshold setting with bounds checking."""
        # Test normal value
        self.validator.set_confidence_threshold(0.8)
        self.assertEqual(self.validator.confidence_threshold, 0.8)
        
        # Test lower bound
        self.validator.set_confidence_threshold(-0.1)
        self.assertEqual(self.validator.confidence_threshold, 0.0)
        
        # Test upper bound
        self.validator.set_confidence_threshold(1.5)
        self.assertEqual(self.validator.confidence_threshold, 1.0)
    
    def test_set_counter_roi(self):
        """Test counter ROI setting."""
        new_roi = (50, 50, 500, 400)
        self.validator.set_counter_roi(new_roi)
        self.assertEqual(self.validator.counter_roi, new_roi)
    
    def test_validation_stats(self):
        """Test validation statistics retrieval."""
        stats = self.validator.get_validation_stats()
        
        self.assertIn("confidence_threshold", stats)
        self.assertIn("min_detection_size", stats)
        self.assertIn("counter_roi", stats)
        self.assertIn("temporal_consistency_frames", stats)
        self.assertIn("recent_detections_count", stats)
        self.assertIn("max_detection_age_seconds", stats)
        
        self.assertEqual(stats["confidence_threshold"], 0.7)
        self.assertEqual(stats["min_detection_size"], 100)
    
    def test_temporal_consistency(self):
        """Test temporal consistency checking."""
        # Disable temporal consistency for first test
        self.validator.temporal_consistency_frames = 1
        
        detection = self.create_test_detection()
        self.assertTrue(self.validator._passes_temporal_consistency(detection))
        
        # Enable temporal consistency
        self.validator.temporal_consistency_frames = 2
        
        # First detection should fail (no history)
        self.assertFalse(self.validator._passes_temporal_consistency(detection))
        
        # Add to recent detections and test again
        self.validator._recent_detections = [detection]
        similar_detection = self.create_test_detection(bbox_x=210, bbox_y=210)  # Similar position
        
        self.assertTrue(self.validator._passes_temporal_consistency(similar_detection))


if __name__ == '__main__':
    unittest.main()