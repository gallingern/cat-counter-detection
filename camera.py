"""
Simple camera interface using OpenCV for Raspberry Pi Camera Module v2.
Optimized for Pi Zero 2 W with imx219 sensor.
"""

import io
import time
import logging
import threading
import cv2
import numpy as np
try:
    from . import config
except ImportError:
    import config

logger = logging.getLogger(__name__)

class Camera:
    """Simple camera interface using OpenCV for Raspberry Pi Camera Module v2.
    Optimized for Pi Zero 2 W with imx219 sensor and improved image quality."""
    
    def __init__(self):
        """Initialize the camera with settings from config."""
        self.resolution = config.CAMERA_RESOLUTION
        self.framerate = config.CAMERA_FRAMERATE
        self.rotation = config.CAMERA_ROTATION
        self.camera = None
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
        
        # Close camera
        if self.camera:
            try:
                self.camera.release()
            except Exception as e:
                logger.error(f"Error closing camera: {e}")
            finally:
                self.camera = None
        
        logger.info("Camera stopped")
    
    def _capture_loop(self):
        """Main capture loop that runs in a separate thread."""
        try:
            logger.info("Starting camera capture loop...")
            
            # Initialize the camera using OpenCV with V4L2 backend
            # This is the correct backend for Raspberry Pi Camera Module v2
            logger.info("Opening camera with V4L2 backend...")
            self.camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
            
            # Don't set any camera properties - let it use native settings
            logger.info("Using camera native settings...")
            
            # Use camera's default format - don't try to change it
            logger.info("Using camera's default format...")
            
            # Check if camera opened successfully
            if not self.camera.isOpened():
                # Try default backend as fallback
                logger.info("V4L2 failed, trying default backend...")
                self.camera = cv2.VideoCapture(0, cv2.CAP_ANY)
                if not self.camera.isOpened():
                    raise RuntimeError("Failed to open camera with any backend")
            
            logger.info("Camera opened successfully")
            
            # Get the camera's current resolution first
            current_width = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
            current_height = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
            logger.info(f"Camera native resolution: {current_width}x{current_height}")

            # Use the camera's native resolution instead of forcing our own
            # We can scale down later in software if needed
            
            # Allow camera to warm up with multiple test reads
            logger.info("Warming up camera...")
            warmup_success = False
            for i in range(10):  # Try up to 10 times
                ret, test_frame = self.camera.read()
                if ret and test_frame is not None:
                    warmup_success = True
                    logger.info(f"Camera warmed up successfully after {i+1} attempts")
                    break
                logger.info(f"Warm-up attempt {i+1} failed")
                time.sleep(0.5)
            
            if not warmup_success:
                logger.warning("Camera warm-up failed, continuing anyway")
            
            # Additional warm-up time
            time.sleep(1)
            
            # Capture frames continuously
            consecutive_failures = 0
            while self.running:
                ret, frame = self.camera.read()
                if not ret:
                    consecutive_failures += 1
                    if consecutive_failures <= 5:
                        logger.warning(f"Failed to read frame from camera (attempt {consecutive_failures})")
                    elif consecutive_failures == 6:
                        logger.error("Multiple consecutive camera read failures - camera may not be accessible")
                    time.sleep(0.1)
                    continue
                
                # Reset failure counter on successful read
                consecutive_failures = 0
                
                # Apply rotation if needed
                if self.rotation == 90:
                    frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                elif self.rotation == 180:
                    frame = cv2.rotate(frame, cv2.ROTATE_180)
                elif self.rotation == 270:
                    frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
                
                # Update the frame
                with self.lock:
                    self.frame = frame.copy()
                    self.last_frame_time = time.time()
                
                # Sleep to maintain framerate
                time.sleep(1.0 / self.framerate)
                
        except Exception as e:
            logger.error(f"Error in camera capture loop: {e}")
            self.running = False
    
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
        return jpeg.tobytes()
