"""Detection validation service implementation."""

import logging
from typing import List, Tuple
from datetime import datetime, timedelta
from ..models.detection import Detection, ValidDetection, BoundingBox
from .interfaces import DetectionValidatorInterface

logger = logging.getLogger(__name__)


class DetectionValidator(DetectionValidatorInterface):
    """Validates and filters raw detections based on business rules."""
    
    def __init__(self, 
                 confidence_threshold: float = 0.7,
                 min_detection_size: int = 50,
                 counter_roi: Tuple[int, int, int, int] = (0, 0, 640, 480),
                 temporal_consistency_frames: int = 2):
        """
        Initialize detection validator.
        
        Args:
            confidence_threshold: Minimum confidence for valid detection
            min_detection_size: Minimum bounding box area in pixels
            counter_roi: Region of interest for counter area (x, y, width, height)
            temporal_consistency_frames: Number of frames detection must persist
        """
        self.confidence_threshold = confidence_threshold
        self.min_detection_size = min_detection_size
        self.counter_roi = counter_roi
        self.temporal_consistency_frames = temporal_consistency_frames
        
        # Track recent detections for temporal consistency
        self._recent_detections: List[Detection] = []
        self._max_detection_age = timedelta(seconds=5)
    
    def validate_detections(self, detections: List[Detection]) -> List[ValidDetection]:
        """Validate raw detections and return filtered valid detections."""
        if not detections:
            return []
        
        valid_detections = []
        
        for detection in detections:
            # Apply validation filters
            if self._passes_confidence_filter(detection):
                if self._passes_size_filter(detection):
                    if self._passes_position_filter(detection):
                        if self._passes_temporal_consistency(detection):
                            valid_detection = self._create_valid_detection(detection)
                            valid_detections.append(valid_detection)
        
        # Update recent detections for temporal consistency
        self._update_recent_detections(detections)
        
        logger.debug(f"Validated {len(valid_detections)} out of {len(detections)} raw detections")
        return valid_detections
    
    def count_cats(self, detections: List[ValidDetection]) -> int:
        """Count the number of cats in validated detections."""
        if not detections:
            return 0
        
        # Use non-maximum suppression to avoid double counting overlapping detections
        unique_detections = self._apply_non_maximum_suppression(detections)
        
        total_cats = sum(detection.cat_count for detection in unique_detections)
        logger.debug(f"Counted {total_cats} cats from {len(unique_detections)} unique detections")
        
        return total_cats
    
    def is_on_counter(self, detection: Detection) -> bool:
        """Check if detection is within the counter area."""
        counter_x, counter_y, counter_w, counter_h = self.counter_roi
        
        for bbox in detection.bounding_boxes:
            # Check if bounding box center is within counter ROI
            center_x = bbox.x + bbox.width // 2
            center_y = bbox.y + bbox.height // 2
            
            if (counter_x <= center_x <= counter_x + counter_w and
                counter_y <= center_y <= counter_y + counter_h):
                return True
        
        return False
    
    def set_confidence_threshold(self, threshold: float) -> None:
        """Update confidence threshold."""
        self.confidence_threshold = max(0.0, min(1.0, threshold))
        logger.info(f"Confidence threshold set to {self.confidence_threshold}")
    
    def set_counter_roi(self, roi: Tuple[int, int, int, int]) -> None:
        """Update counter region of interest."""
        self.counter_roi = roi
        logger.info(f"Counter ROI set to {roi}")
    
    def _passes_confidence_filter(self, detection: Detection) -> bool:
        """Check if detection meets confidence threshold."""
        return detection.raw_confidence >= self.confidence_threshold
    
    def _passes_size_filter(self, detection: Detection) -> bool:
        """Check if detection bounding boxes meet minimum size requirement."""
        for bbox in detection.bounding_boxes:
            if bbox.area() >= self.min_detection_size:
                return True
        return False
    
    def _passes_position_filter(self, detection: Detection) -> bool:
        """Check if detection is in the counter area."""
        return self.is_on_counter(detection)
    
    def _passes_temporal_consistency(self, detection: Detection) -> bool:
        """Check if detection has temporal consistency (appears in multiple frames)."""
        if self.temporal_consistency_frames <= 1:
            return True
        
        # Count similar detections in recent history
        similar_count = 0
        current_time = detection.timestamp
        
        for recent_detection in self._recent_detections:
            # Check if recent detection is within time window
            if (current_time - recent_detection.timestamp) <= self._max_detection_age:
                if self._detections_are_similar(detection, recent_detection):
                    similar_count += 1
        
        return similar_count >= (self.temporal_consistency_frames - 1)
    
    def _detections_are_similar(self, det1: Detection, det2: Detection) -> bool:
        """Check if two detections are similar (same object in similar position)."""
        if not det1.bounding_boxes or not det2.bounding_boxes:
            return False
        
        # Compare primary bounding boxes
        bbox1 = det1.bounding_boxes[0]
        bbox2 = det2.bounding_boxes[0]
        
        # Calculate IoU (Intersection over Union)
        iou = self._calculate_iou(bbox1, bbox2)
        
        # Consider similar if IoU > 0.3 (moderate overlap)
        return iou > 0.3
    
    def _calculate_iou(self, bbox1: BoundingBox, bbox2: BoundingBox) -> float:
        """Calculate Intersection over Union of two bounding boxes."""
        # Calculate intersection
        x1 = max(bbox1.x, bbox2.x)
        y1 = max(bbox1.y, bbox2.y)
        x2 = min(bbox1.x + bbox1.width, bbox2.x + bbox2.width)
        y2 = min(bbox1.y + bbox1.height, bbox2.y + bbox2.height)
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        
        # Calculate union
        area1 = bbox1.area()
        area2 = bbox2.area()
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _create_valid_detection(self, detection: Detection) -> ValidDetection:
        """Create a ValidDetection from a raw Detection."""
        # Count cats in this detection (usually 1 per detection)
        cat_count = len([bbox for bbox in detection.bounding_boxes 
                        if bbox.area() >= self.min_detection_size])
        
        # Calculate validated confidence (could be enhanced with additional factors)
        validated_confidence = min(detection.raw_confidence * 1.1, 1.0)
        
        return ValidDetection(
            timestamp=detection.timestamp,
            bounding_boxes=detection.bounding_boxes,
            frame_width=detection.frame_width,
            frame_height=detection.frame_height,
            raw_confidence=detection.raw_confidence,
            cat_count=cat_count,
            is_on_counter=True,  # Already filtered for counter position
            validated_confidence=validated_confidence
        )
    
    def _apply_non_maximum_suppression(self, detections: List[ValidDetection]) -> List[ValidDetection]:
        """Apply non-maximum suppression to remove overlapping detections."""
        if len(detections) <= 1:
            return detections
        
        # Sort by confidence (highest first)
        sorted_detections = sorted(detections, 
                                 key=lambda d: d.validated_confidence, 
                                 reverse=True)
        
        unique_detections = []
        
        for detection in sorted_detections:
            is_unique = True
            
            for unique_detection in unique_detections:
                if self._detections_are_similar(detection, unique_detection):
                    is_unique = False
                    break
            
            if is_unique:
                unique_detections.append(detection)
        
        return unique_detections
    
    def _update_recent_detections(self, new_detections: List[Detection]) -> None:
        """Update the list of recent detections for temporal consistency."""
        current_time = datetime.now()
        
        # Remove old detections
        self._recent_detections = [
            det for det in self._recent_detections
            if (current_time - det.timestamp) <= self._max_detection_age
        ]
        
        # Add new detections
        self._recent_detections.extend(new_detections)
        
        # Limit size to prevent memory growth
        max_recent_detections = 50
        if len(self._recent_detections) > max_recent_detections:
            self._recent_detections = self._recent_detections[-max_recent_detections:]
    
    def get_validation_stats(self) -> dict:
        """Get validation statistics and current settings."""
        return {
            "confidence_threshold": self.confidence_threshold,
            "min_detection_size": self.min_detection_size,
            "counter_roi": self.counter_roi,
            "temporal_consistency_frames": self.temporal_consistency_frames,
            "recent_detections_count": len(self._recent_detections),
            "max_detection_age_seconds": self._max_detection_age.total_seconds()
        }