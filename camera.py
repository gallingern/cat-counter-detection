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
            # Initialize the camera using OpenCV with V4L2 backend
            # This is the correct backend for Raspberry Pi Camera Module v2
            self.camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
            
            # Set camera properties - use more conservative settings initially
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # Start with lower resolution
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 15)
            
            # Try multiple formats - start with auto-detect, then specific formats
            formats_to_try = [
                None,  # Auto-detect
                cv2.VideoWriter_fourcc('Y', 'U', 'Y', 'V'),  # YUYV
                cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'),  # MJPG
                cv2.VideoWriter_fourcc('R', 'G', 'B', '3'),  # RGB3
            ]
            
            format_working = False
            for fmt in formats_to_try:
                if fmt:
                    self.camera.set(cv2.CAP_PROP_FOURCC, fmt)
                    logger.info(f"Trying format: {fmt}")
                
                # Test if we can read a frame
                ret, test_frame = self.camera.read()
                if ret and test_frame is not None:
                    format_working = True
                    logger.info(f"Format working: {fmt if fmt else 'auto-detect'}")
                    break
                else:
                    logger.info(f"Format failed: {fmt if fmt else 'auto-detect'}")
            
            if not format_working:
                logger.warning("All formats failed, continuing with auto-detect")
            
            # Check if camera opened successfully
            if not self.camera.isOpened():
                # Try default backend as fallback
                logger.info("V4L2 failed, trying default backend...")
                self.camera = cv2.VideoCapture(0, cv2.CAP_ANY)
                if not self.camera.isOpened():
                    raise RuntimeError("Failed to open camera with any backend")
            
            logger.info("Camera opened successfully")
            
            # Now try to set the desired resolution
            actual_width = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
            logger.info(f"Camera initialized with resolution {actual_width}x{actual_height}")
            
            # If we got a lower resolution, try to upgrade to desired resolution
            if actual_width < self.resolution[0] or actual_height < self.resolution[1]:
                logger.info(f"Attempting to set resolution to {self.resolution[0]}x{self.resolution[1]}...")
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
                
                # Check if the change was successful
                new_width = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
                new_height = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
                logger.info(f"Camera resolution set to {new_width}x{new_height}")
            
            # Allow camera to warm up with multiple test reads
            logger.info("Warming up camera...")
            warmup_success = False
            for i in range(10):  # Try up to 10 times
                ret, test_frame = self.camera.read()
                if ret and test_frame is not None:
                    warmup_success = True
                    logger.info(f"Camera warmed up successfully after {i+1} attempts")
                    break
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
