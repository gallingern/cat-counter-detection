"""
Simple configuration for cat detection system.
"""

# Camera settings
CAMERA_RESOLUTION = (640, 480)  # Width, Height
CAMERA_FRAMERATE = 10  # FPS
CAMERA_ROTATION = 0  # Degrees (0, 90, 180, or 270)

# Detection settings
CONFIDENCE_THRESHOLD = 0.5  # Minimum confidence for detection
DETECTION_INTERVAL = 0.1  # Seconds between detection attempts

# Web server settings
WEB_PORT = 5000
WEB_HOST = '0.0.0.0'  # Listen on all interfaces
DEBUG_MODE = False

# Paths
CASCADE_PATH = '/usr/local/share/opencv4/haarcascades/haarcascade_frontalcatface.xml'