"""Detection data models."""

from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class BoundingBox:
    """Represents a bounding box around a detected object."""
    x: int
    y: int
    width: int
    height: int
    confidence: float

    def area(self) -> int:
        """Calculate the area of the bounding box."""
        return self.width * self.height

    def center(self) -> tuple[int, int]:
        """Get the center point of the bounding box."""
        return (self.x + self.width // 2, self.y + self.height // 2)


@dataclass
class Detection:
    """Base detection result from the detection engine."""
    timestamp: datetime
    bounding_boxes: List[BoundingBox]
    frame_width: int
    frame_height: int
    raw_confidence: float


@dataclass
class ValidDetection(Detection):
    """Validated detection that has passed all filtering criteria."""
    cat_count: int
    is_on_counter: bool
    validated_confidence: float


@dataclass
class DetectionRecord:
    """Historical detection record for storage."""
    timestamp: datetime
    cat_count: int
    confidence_score: float
    image_path: str
    bounding_boxes: List[BoundingBox]