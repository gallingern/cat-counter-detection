"""
Simple configuration for cat detection system.
Ultra-optimized for maximum efficiency on Raspberry Pi Zero 2 W with Camera Module v2.
"""

# Camera settings (ultra-maximum efficiency)
CAMERA_RESOLUTION = (160, 120)  # Ultra-low resolution for maximum efficiency
CAMERA_FRAMERATE = 0.5  # 0.5 FPS (1 frame every 2 seconds) for ultra efficiency
CAMERA_ROTATION = 0  # Degrees (0, 90, 180, or 270)

# Detection settings (ultra-maximum efficiency)
CONFIDENCE_THRESHOLD = 0.4  # Lower threshold for v2's better image quality
DETECTION_INTERVAL = 5.0  # Detect every 5 seconds (ultra conservative)
MOTION_THRESHOLD = 5000  # Very high threshold - only detect major motion

# Web server settings
WEB_PORT = 5000
WEB_HOST = '0.0.0.0'  # Listen on all interfaces
DEBUG_MODE = False

# Paths
CASCADE_PATH = '/usr/local/share/opencv4/haarcascades/haarcascade_frontalcatface.xml'
