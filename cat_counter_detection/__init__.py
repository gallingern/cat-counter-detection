"""
Cat Counter Detection System

A computer vision system for Raspberry Pi Zero W with Camera Module v2
to detect cats on kitchen counters and provide real-time notifications.
"""

__version__ = "1.0.0"
__author__ = "Cat Counter Detection System"

# Import core components
from .config_manager import ConfigManager
from .models import (
    BoundingBox,
    Detection,
    ValidDetection,
    DetectionRecord,
    SystemConfig,
    StorageStats
)
from .services import (
    FrameCaptureServiceInterface,
    DetectionEngineInterface,
    DetectionValidatorInterface,
    NotificationServiceInterface,
    StorageServiceInterface,
    SystemMonitorInterface
)
from . import utils

__all__ = [
    # Core management
    'ConfigManager',
    
    # Data models
    'BoundingBox',
    'Detection',
    'ValidDetection',
    'DetectionRecord',
    'SystemConfig',
    'StorageStats',
    
    # Service interfaces
    'FrameCaptureServiceInterface',
    'DetectionEngineInterface',
    'DetectionValidatorInterface',
    'NotificationServiceInterface',
    'StorageServiceInterface',
    'SystemMonitorInterface',
    
    # Utilities
    'utils'
]