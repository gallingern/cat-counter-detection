"""
Simple cat detector using OpenCV Haar cascades.
Optimized for Raspberry Pi Zero 2 W with Camera Module v2.
"""

import cv2
import logging
import os
import time
try:
    from . import config
except ImportError:
    import config

logger = logging.getLogger(__name__)

class CatDetector:
    """Simple cat detector using OpenCV Haar cascades.
    Optimized for Camera Module v2 with improved detection parameters."""
    
    def __init__(self):
        """Initialize the cat detector."""
        self.cascade_path = config.CASCADE_PATH
        self.confidence_threshold = config.CONFIDENCE_THRESHOLD
        self.last_detection_time = 0
        self.detection_interval = config.DETECTION_INTERVAL
        self.cascade = None
        self.load_cascade()
        
    def load_cascade(self):
        """Load the Haar cascade classifier."""
        try:
            # Try the configured path first
            if os.path.exists(self.cascade_path):
                self.cascade = cv2.CascadeClassifier(self.cascade_path)
                if self.cascade.empty():
                    logger.error(f"Failed to load cascade from {self.cascade_path}")
                else:
                    logger.info(f"Loaded cascade from {self.cascade_path}")
                    return
            
            # Try the default OpenCV installation paths
            opencv_paths = [
                '/usr/local/share/opencv4/haarcascades/haarcascade_frontalcatface.xml',
                '/usr/share/opencv4/haarcascades/haarcascade_frontalcatface.xml',
                '/usr/local/share/opencv/haarcascades/haarcascade_frontalcatface.xml',
                '/usr/share/opencv/haarcascades/haarcascade_frontalcatface.xml'
            ]
            
            for path in opencv_paths:
                if os.path.exists(path):
                    self.cascade = cv2.CascadeClassifier(path)
                    if not self.cascade.empty():
                        logger.info(f"Loaded cascade from {path}")
                        return
                    else:
                        logger.warning(f"Failed to load cascade from {path}")
            
            logger.error("Could not find or load cat cascade file")
            raise FileNotFoundError("Cat cascade file not found or invalid")
            
        except Exception as e:
            logger.error(f"Error loading cascade: {e}")
            raise
    
    def detect(self, frame):
        """
        Detect cats in the frame.
        
        Args:
            frame: BGR image as numpy array
            
        Returns:
            (detections, annotated_frame) where:
                - detections is a list of (x, y, w, h) tuples
                - annotated_frame is the input frame with detection boxes drawn
        """
        # Check if cascade is loaded
        if self.cascade is None or self.cascade.empty():
            logger.error("Cascade classifier not loaded")
            return [], frame
        
        # Skip detection if it's too soon since the last one
        current_time = time.time()
        if current_time - self.last_detection_time < self.detection_interval:
            return [], frame
        
        self.last_detection_time = current_time
        
        # Convert to grayscale for detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect cats (optimized for Camera Module v2)
        cats = self.cascade.detectMultiScale(
            gray,
            scaleFactor=1.05,  # More sensitive for v2's better image quality
            minNeighbors=3,    # Lower threshold for better detection
            minSize=(40, 40)   # Larger minimum size for v2's higher resolution
        )
        
        # Draw rectangles around detected cats
        annotated_frame = frame.copy()
        for (x, y, w, h) in cats:
            cv2.rectangle(annotated_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(annotated_frame, 'Cat', (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        
        # Add detection count
        cv2.putText(annotated_frame, f'Cats: {len(cats)}', (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        return cats, annotated_frame