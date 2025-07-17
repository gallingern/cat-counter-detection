"""Service interfaces and abstract base classes."""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Union, Any
from datetime import datetime

from ..models.detection import Detection, ValidDetection, DetectionRecord
from ..models.config import SystemConfig, StorageStats

# Handle numpy import gracefully for development
try:
    import numpy as np
    NDArray = np.ndarray
except ImportError:
    # Fallback type hint for development without numpy
    NDArray = Any


class FrameCaptureServiceInterface(ABC):
    """Interface for camera frame capture service."""
    
    @abstractmethod
    def start_capture(self) -> None:
        """Start camera capture."""
        pass
    
    @abstractmethod
    def get_frame(self) -> Optional[NDArray]:
        """Get the latest frame from camera."""
        pass
    
    @abstractmethod
    def stop_capture(self) -> None:
        """Stop camera capture."""
        pass
    
    @abstractmethod
    def is_camera_available(self) -> bool:
        """Check if camera is available."""
        pass


class DetectionEngineInterface(ABC):
    """Interface for cat detection engine."""
    
    @abstractmethod
    def load_model(self, model_path: str) -> None:
        """Load detection model."""
        pass
    
    @abstractmethod
    def detect_cats(self, frame: NDArray) -> List[Detection]:
        """Detect cats in frame."""
        pass
    
    @abstractmethod
    def set_confidence_threshold(self, threshold: float) -> None:
        """Set detection confidence threshold."""
        pass
    
    @abstractmethod
    def set_roi(self, roi: Tuple[int, int, int, int]) -> None:
        """Set region of interest for detection."""
        pass


class DetectionValidatorInterface(ABC):
    """Interface for detection validation."""
    
    @abstractmethod
    def validate_detections(self, detections: List[Detection]) -> List[ValidDetection]:
        """Validate raw detections."""
        pass
    
    @abstractmethod
    def count_cats(self, detections: List[ValidDetection]) -> int:
        """Count cats in validated detections."""
        pass
    
    @abstractmethod
    def is_on_counter(self, detection: Detection) -> bool:
        """Check if detection is on counter."""
        pass


class NotificationServiceInterface(ABC):
    """Interface for notification service."""
    
    @abstractmethod
    def send_push_notification(self, message: str, image_path: str) -> bool:
        """Send push notification."""
        pass
    
    @abstractmethod
    def send_email(self, subject: str, body: str, image_path: str) -> bool:
        """Send email notification."""
        pass
    
    @abstractmethod
    def queue_notification(self, notification_type: str, message: str, image_path: str) -> None:
        """Queue notification for later delivery."""
        pass
    
    @abstractmethod
    def process_queue(self) -> None:
        """Process queued notifications."""
        pass


class StorageServiceInterface(ABC):
    """Interface for storage service."""
    
    @abstractmethod
    def save_detection(self, detection: ValidDetection, image: NDArray) -> str:
        """Save detection and return image path."""
        pass
    
    @abstractmethod
    def get_detection_history(self, start_date: datetime, end_date: datetime) -> List[DetectionRecord]:
        """Get detection history for date range."""
        pass
    
    @abstractmethod
    def cleanup_old_data(self) -> None:
        """Clean up old detection data."""
        pass
    
    @abstractmethod
    def get_storage_usage(self) -> StorageStats:
        """Get storage usage statistics."""
        pass


class SystemMonitorInterface(ABC):
    """Interface for system monitoring and health checks."""
    
    @abstractmethod
    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        pass
    
    @abstractmethod
    def get_memory_usage(self) -> float:
        """Get current memory usage percentage."""
        pass
    
    @abstractmethod
    def get_temperature(self) -> float:
        """Get system temperature in Celsius."""
        pass
    
    @abstractmethod
    def is_service_healthy(self, service_name: str) -> bool:
        """Check if a service is healthy."""
        pass
    
    @abstractmethod
    def restart_service(self, service_name: str) -> bool:
        """Restart a failed service."""
        pass
    
    @abstractmethod
    def trigger_garbage_collection(self) -> None:
        """Trigger garbage collection to free memory."""
        pass