"""
Simple configuration for cat detection system.
Optimized for maximum efficiency on Raspberry Pi Zero 2 W with Camera Module v2.
"""

# Camera settings (maximum efficiency)
CAMERA_RESOLUTION = (320, 240)  # Very low resolution for maximum efficiency
CAMERA_FRAMERATE = 1  # 1 FPS for efficiency
CAMERA_ROTATION = 0  # Degrees (0, 90, 180, or 270)

# Detection settings (maximum efficiency)
CONFIDENCE_THRESHOLD = 0.4  # Lower threshold for v2's better image quality
DETECTION_INTERVAL = 2.0  # Detect every 2 seconds (very conservative)
MOTION_THRESHOLD = 2000  # Higher threshold - only detect significant motion

# Web server settings
WEB_PORT = 5000
WEB_HOST = '0.0.0.0'  # Listen on all interfaces
DEBUG_MODE = False

# Paths
CASCADE_PATH = '/usr/local/share/opencv4/haarcascades/haarcascade_frontalcatface.xml'
