"""
Simple camera interface for Raspberry Pi Camera Module.
"""

import io
import time
import logging
import threading
import picamera
from picamera.array import PiRGBArray
import numpy as np
import config

logger = logging.getLogger(__name__)

class Camera:
    """Simple camera interface for Raspberry Pi Camera Module."""
    
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
        if hasattr(self, 'thread'):
            self.thread.join(timeout=2.0)
        
        if self.camera:
            self.camera.close()
            self.camera = None
        
        logger.info("Camera stopped")
    
    def _capture_loop(self):
        """Main capture loop that runs in a separate thread."""
        try:
            # Initialize the camera
            self.camera = picamera.PiCamera()
            self.camera.resolution = self.resolution
            self.camera.framerate = self.framerate
            self.camera.rotation = self.rotation
            
            # Allow camera to warm up
            time.sleep(2)
            
            # Create a stream for capturing frames
            raw_capture = PiRGBArray(self.camera, size=self.resolution)
            
            # Capture frames continuously
            for frame in self.camera.capture_continuous(raw_capture, format="bgr", 
                                                      use_video_port=True):
                if not self.running:
                    break
                
                # Get the numpy array
                image = frame.array
                
                # Update the frame
                with self.lock:
                    self.frame = image.copy()
                    self.last_frame_time = time.time()
                
                # Clear the stream for the next frame
                raw_capture.truncate(0)
                
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
        import cv2
        ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return jpeg.tobytes()