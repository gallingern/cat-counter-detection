"""Services for the cat detection system."""

from .interfaces import (
    FrameCaptureServiceInterface,
    DetectionEngineInterface,
    DetectionValidatorInterface,
    NotificationServiceInterface,
    StorageServiceInterface,
    SystemMonitorInterface
)

__all__ = [
    'FrameCaptureServiceInterface',
    'DetectionEngineInterface', 
    'DetectionValidatorInterface',
    'NotificationServiceInterface',
    'StorageServiceInterface',
    'SystemMonitorInterface'
]