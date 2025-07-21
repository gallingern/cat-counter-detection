"""
Simple camera interface using libcamera-vid subprocess for Raspberry Pi Camera Module v2.
Optimized for maximum efficiency on Pi Zero 2 W.
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
    """Simple camera interface using libcamera-vid subprocess for Raspberry Pi Camera Module v2.
    Optimized for maximum efficiency on Pi Zero 2 W."""
    
    def __init__(self):
        """Initialize the camera with settings from config."""
        self.resolution = config.CAMERA_RESOLUTION
        self.framerate = config.CAMERA_FRAMERATE
        self.rotation = config.CAMERA_ROTATION
        self.frame = None
        self.last_frame_time = 0
        self.running = False
        self.lock = threading.Lock()
        self.process = None
        self.motion_detected = False
        self.last_frame_gray = None
        self.motion_threshold = config.MOTION_THRESHOLD
        
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
        
        # Stop the libcamera-vid process
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                logger.error(f"Error stopping libcamera-vid process: {e}")
            finally:
                self.process = None
        
        # Wait for thread to finish
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join(timeout=2.0)
            if self.thread.is_alive():
                logger.warning("Camera thread did not stop gracefully")
        
        logger.info("Camera stopped")
    
    def _detect_motion(self, current_frame):
        """Detect motion by comparing with previous frame."""
        if self.last_frame_gray is None:
            self.last_frame_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
            return False
        
        # Convert current frame to grayscale
        current_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate frame difference
        frame_diff = cv2.absdiff(current_gray, self.last_frame_gray)
        
        # Count pixels that changed significantly
        changed_pixels = np.sum(frame_diff > 30)
        
        # Update last frame
        self.last_frame_gray = current_gray
        
        # Return True if enough pixels changed
        return changed_pixels > self.motion_threshold
    
    def _capture_loop(self):
        """Main capture loop that runs in a separate thread using libcamera-vid."""
        try:
            logger.info("Starting camera capture loop with libcamera-vid (optimized)...")
            width, height = self.resolution
            
            # Start libcamera-vid process with optimized parameters
            cmd = [
                '/usr/bin/libcamera-vid',
                '-n',  # No preview
                '--width', str(width),
                '--height', str(height),
                '--framerate', str(self.framerate),
                '--codec', 'mjpeg',  # Use MJPEG for easier frame extraction
                '--quality', '70',  # Lower quality for efficiency
                '--bitrate', '1000000',  # 1Mbps bitrate
                '--inline',  # Inline headers for efficiency
                '--flush',  # Flush buffers immediately
                '-t', '0',  # Run indefinitely
                '-o', '-'  # Output to stdout
            ]
            
            logger.info(f"Starting libcamera-vid with optimized command: {' '.join(cmd)}")
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            
            # Allow camera to warm up
            logger.info("Warming up camera...")
            time.sleep(2)
            
            # Read frames from the stream with optimized buffer management
            frame_buffer = b''
            frame_count = 0
            
            while self.running:
                try:
                    # Read data from the process with smaller chunks for efficiency
                    chunk = self.process.stdout.read(1024)
                    if not chunk:
                        logger.warning("No data received from libcamera-vid")
                        break
                    
                    frame_buffer += chunk
                    
                    # Look for JPEG frame boundaries
                    while b'\xff\xd8' in frame_buffer and b'\xff\xd9' in frame_buffer:
                        start = frame_buffer.find(b'\xff\xd8')
                        end = frame_buffer.find(b'\xff\xd9', start) + 2
                        
                        if end > start:
                            # Extract complete JPEG frame
                            jpeg_data = frame_buffer[start:end]
                            frame_buffer = frame_buffer[end:]
                            
                            # Decode JPEG to numpy array with optimized parameters
                            arr = np.frombuffer(jpeg_data, dtype=np.uint8)
                            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                            
                            if frame is not None:
                                frame_count += 1
                                
                                # Apply rotation if needed
                                if self.rotation == 90:
                                    frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                                elif self.rotation == 180:
                                    frame = cv2.rotate(frame, cv2.ROTATE_180)
                                elif self.rotation == 270:
                                    frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
                                
                                # Detect motion
                                motion = self._detect_motion(frame)
                                self.motion_detected = motion
                                
                                with self.lock:
                                    self.frame = frame.copy()
                                    self.last_frame_time = time.time()
                                
                                # Log motion detection occasionally
                                if frame_count % 10 == 0 and motion:
                                    logger.info(f"Motion detected at frame {frame_count}")
                                    
                            else:
                                logger.warning("Failed to decode JPEG frame")
                        else:
                            break
                            
                except Exception as e:
                    logger.error(f"Error reading from libcamera-vid: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Error in camera capture loop: {e}")
        finally:
            self.running = False

    def get_frame(self):
        """Get the latest frame from the camera."""
        with self.lock:
            if self.frame is None:
                return None
            return self.frame.copy()
    
    def get_motion_status(self):
        """Get current motion detection status."""
        return self.motion_detected
    
    def get_jpeg(self, quality=70):
        """Get the latest frame as JPEG bytes with optimized quality."""
        frame = self.get_frame()
        if frame is None:
            return None
        # Convert to JPEG with optimized quality
        ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return jpeg.tobytes() if ret else None
