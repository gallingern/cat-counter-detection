"""Default configuration values and constants."""

from typing import Dict, Any

# Default system configuration
DEFAULT_CONFIG: Dict[str, Any] = {
    # Detection settings
    "confidence_threshold": 0.7,
    "detection_roi": [0, 0, 640, 480],
    "detection_sensitivity": "medium",
    "min_detection_size": 50,
    "temporal_consistency_frames": 2,
    
    # Monitoring schedule
    "monitoring_enabled": True,
    "monitoring_start_hour": 0,
    "monitoring_end_hour": 23,
    "monitoring_days": [True, True, True, True, True, True, True],  # Mon-Sun
    
    # Notification settings
    "push_notifications_enabled": True,
    "email_notifications_enabled": False,
    "notification_cooldown_minutes": 5,
    "notification_max_per_hour": 12,
    "notification_quiet_hours_start": 22,
    "notification_quiet_hours_end": 7,
    "notification_quiet_hours_enabled": False,
    
    # Storage settings
    "max_storage_days": 30,
    "image_quality": 85,
    "auto_cleanup_enabled": True,
    
    # Performance settings
    "target_fps": 1.0,
    "max_cpu_usage": 50.0,
    "adaptive_performance": True
}

# System constants
SYSTEM_CONSTANTS = {
    "MIN_DETECTION_SIZE": 50,  # Minimum bounding box size in pixels
    "MAX_DETECTION_AGE_SECONDS": 5,  # Maximum age for temporal consistency
    "NOTIFICATION_RETRY_ATTEMPTS": 3,
    "STORAGE_CLEANUP_INTERVAL_HOURS": 24,
    "HEALTH_CHECK_INTERVAL_SECONDS": 30,
    "CAMERA_WARMUP_TIME_SECONDS": 2,
    "MAX_QUEUE_SIZE": 100,
    "LOG_ROTATION_SIZE_MB": 10
}

# File paths and directories
DEFAULT_PATHS = {
    "config_file": "config.json",
    "storage_dir": "data",
    "images_dir": "data/images",
    "logs_dir": "logs",
    "models_dir": "models",
    "database_file": "data/detections.db"
}

# Camera settings optimized for Pi Zero W
CAMERA_SETTINGS = {
    "resolution": (640, 480),
    "framerate": 1,
    "iso": 0,  # Auto ISO
    "exposure_mode": "auto",
    "awb_mode": "auto",
    "image_effect": "none",
    "rotation": 0,
    "hflip": False,
    "vflip": False
}

# Detection model settings
MODEL_SETTINGS = {
    "haar_cascade_path": "models/haarcascade_frontalcatface.xml",
    "mobilenet_model_path": "models/cat_detection_mobilenet.tflite",
    "input_size": (224, 224),
    "quantization": "int8",
    "num_threads": 2  # Optimized for Pi Zero W
}