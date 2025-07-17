"""Configuration data models."""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class SystemConfig:
    """System configuration settings."""
    # Detection settings
    confidence_threshold: float = 0.7
    detection_roi: Tuple[int, int, int, int] = (0, 0, 640, 480)
    detection_sensitivity: str = "medium"  # low, medium, high
    min_detection_size: int = 50  # Minimum bounding box size in pixels
    temporal_consistency_frames: int = 2  # Frames required for consistent detection
    
    # Monitoring schedule
    monitoring_enabled: bool = True
    monitoring_start_hour: int = 0
    monitoring_end_hour: int = 23
    monitoring_days: Tuple[bool, bool, bool, bool, bool, bool, bool] = (True, True, True, True, True, True, True)  # Mon-Sun
    
    # Notification settings
    push_notifications_enabled: bool = True
    email_notifications_enabled: bool = False
    notification_cooldown_minutes: int = 5
    notification_max_per_hour: int = 12  # Rate limiting
    notification_quiet_hours_start: int = 22  # 10 PM
    notification_quiet_hours_end: int = 7    # 7 AM
    notification_quiet_hours_enabled: bool = False
    
    # Storage settings
    max_storage_days: int = 30
    image_quality: int = 85
    auto_cleanup_enabled: bool = True
    
    # Performance settings
    target_fps: float = 1.0
    max_cpu_usage: float = 50.0
    adaptive_performance: bool = True  # Automatically adjust based on system load


@dataclass
class StorageStats:
    """Storage usage statistics."""
    total_space_mb: float
    used_space_mb: float
    available_space_mb: float
    detection_count: int
    oldest_detection: str
    newest_detection: str