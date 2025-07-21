"""
Simple configuration for cat detection system.
Optimized for Raspberry Pi Zero 2 W with Camera Module v2.
"""

# Camera settings (optimized for efficiency)
CAMERA_RESOLUTION = (640, 480)  # Lower resolution for efficiency
CAMERA_FRAMERATE = 1  # 1 FPS for efficiency
CAMERA_ROTATION = 0  # Degrees (0, 90, 180, or 270)

# Detection settings (optimized for efficiency)
CONFIDENCE_THRESHOLD = 0.4  # Lower threshold for v2's better image quality
DETECTION_INTERVAL = 1.0  # Detect every 1 second (matches frame rate)
MOTION_THRESHOLD = 1000  # Minimum pixel difference for motion detection

# Web server settings
WEB_PORT = 5000
WEB_HOST = '0.0.0.0'  # Listen on all interfaces
DEBUG_MODE = False

# Paths
CASCADE_PATH = '/usr/local/share/opencv4/haarcascades/haarcascade_frontalcatface.xml'
