"""
Simple configuration for cat detection system.
Optimized for Raspberry Pi Zero 2 W with Camera Module v2.
"""

# Camera settings (optimized for Camera Module v2)
CAMERA_RESOLUTION = (1280, 720)  # Width, Height - v2 supports higher resolution
CAMERA_FRAMERATE = 15  # FPS - v2 can handle higher framerate
CAMERA_ROTATION = 0  # Degrees (0, 90, 180, or 270)

# Detection settings (optimized for Camera Module v2)
CONFIDENCE_THRESHOLD = 0.4  # Lower threshold for v2's better image quality
DETECTION_INTERVAL = 0.05  # Faster detection for v2's higher framerate

# Web server settings
WEB_PORT = 5000
WEB_HOST = '0.0.0.0'  # Listen on all interfaces
DEBUG_MODE = False

# Paths
CASCADE_PATH = '/usr/local/share/opencv4/haarcascades/haarcascade_frontalcatface.xml'