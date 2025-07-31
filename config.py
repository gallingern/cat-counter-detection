"""
Simple configuration for cat detector system.
Ultra-optimized for maximum efficiency on Raspberry Pi Zero 2 W with Camera Module v2.
"""

# Camera settings (balanced efficiency)
CAMERA_RESOLUTION = (320, 240)  # Low resolution for efficiency
CAMERA_FRAMERATE = 2.0  # 2 FPS for reasonable responsiveness
CAMERA_ROTATION = 0  # Degrees (0, 90, 180, or 270)

# Detection settings (balanced efficiency)
CONFIDENCE_THRESHOLD = 0.4  # Lower threshold for v2's better image quality
DETECTION_INTERVAL = 2.0  # Detect every 2 seconds
MOTION_THRESHOLD = 2000  # Moderate threshold for motion detection

# Web server settings
WEB_PORT = 5000
WEB_HOST = '0.0.0.0'  # Listen on all interfaces
DEBUG_MODE = False

# Paths
MODEL_PATH = 'models/ssdlite_mobilenet_v2_int8.tflite'
