"""
Simple camera interface using libcamera-still subprocess for Raspberry Pi Camera Module v2.
Optimized for Pi Zero 2 W with imx219 sensor.
"""

import io
import time
import logging
import threading
import subprocess
import numpy as np
import cv2
try:
    from . import config
except ImportError:
    import config

logger = logging.getLogger(__name__)

class Camera:
    """Simple camera interface using libcamera-still subprocess for Raspberry Pi Camera Module v2."""
    
    def __init__(self):
        """Initialize the camera with settings from config."""
        self.resolution = config.CAMERA_RESOLUTION
        self.framerate = config.CAMERA_FRAMERATE
        self.rotation = config.CAMERA_ROTATION
        self.frame = None
        self.last_frame_time = 0
        self.running = False
        self.lock = threading.Lock()
        
        logger.info(f"Camera initialized with resolution {self.resolution}, "
                   f"framerate {self.framerate}, rotation {self.rotation}")
    
    def start(self):
        """Start the camera capture thread."""
        if self.running:
            logger.warning("Camera is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop)
        self.thread.daemon = True
        self.thread.start()
        logger.info("Camera started")
    
    def stop(self):
        """Stop the camera capture thread."""
        self.running = False
        
        # Wait for thread to finish
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join(timeout=2.0)
            if self.thread.is_alive():
                logger.warning("Camera thread did not stop gracefully")
        
        logger.info("Camera stopped")
    
    def _capture_loop(self):
        """Main capture loop that runs in a separate thread using libcamera-still."""
        try:
            logger.info("Starting camera capture loop with libcamera-still...")
            width, height = self.resolution
            interval = 1.0 / self.framerate
            warmup_success = False
            for i in range(10):
                frame = self._capture_frame(width, height)
                if frame is not None:
                    warmup_success = True
                    logger.info(f"Camera warmed up successfully after {i+1} attempts")
                    break
                logger.info(f"Warm-up attempt {i+1} failed")
                time.sleep(0.5)
            if not warmup_success:
                logger.warning("Camera warm-up failed, continuing anyway")
            time.sleep(1)
            while self.running:
                frame = self._capture_frame(width, height)
                if frame is not None:
                    # Apply rotation if needed
                    if self.rotation == 90:
                        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                    elif self.rotation == 180:
                        frame = cv2.rotate(frame, cv2.ROTATE_180)
                    elif self.rotation == 270:
                        frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
                    with self.lock:
                        self.frame = frame.copy()
                        self.last_frame_time = time.time()
                else:
                    logger.warning("Failed to capture frame from libcamera-still")
                time.sleep(interval)
        except Exception as e:
            logger.error(f"Error in camera capture loop: {e}")
            self.running = False

    def _capture_frame(self, width, height):
        """Capture a single frame using libcamera-still and return as numpy array (BGR)."""
        try:
            cmd = [
                'libcamera-still',
                '-n',  # No preview
                '-t', '1',  # Minimal timeout (ms)
                '--width', str(width),
                '--height', str(height),
                '--encoding', 'jpeg',
                '-o', '-'  # Output to stdout
            ]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
            if proc.returncode != 0:
                logger.error(f"libcamera-still error: {proc.stderr.decode().strip()}")
                return None
            jpeg_bytes = proc.stdout
            if not jpeg_bytes:
                logger.warning("No data received from libcamera-still")
                return None
            # Decode JPEG to numpy array (BGR)
            arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if frame is None:
                logger.warning("Failed to decode JPEG from libcamera-still output")
            return frame
        except Exception as e:
            logger.error(f"Exception in _capture_frame: {e}")
            return None

    def get_frame(self):
        """Get the latest frame from the camera."""
        with self.lock:
            if self.frame is None:
                return None
            return self.frame.copy()
    
    def get_jpeg(self, quality=90):
        """Get the latest frame as JPEG bytes."""
        frame = self.get_frame()
        if frame is None:
            return None
        # Convert to JPEG
        ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return jpeg.tobytes() if ret else None
