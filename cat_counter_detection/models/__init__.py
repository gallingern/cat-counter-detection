"""Data models for the cat counter detection system."""

from .detection import BoundingBox, Detection, ValidDetection, DetectionRecord
from .config import SystemConfig, StorageStats

__all__ = ['BoundingBox', 'Detection', 'ValidDetection', 'DetectionRecord', 'SystemConfig', 'StorageStats']