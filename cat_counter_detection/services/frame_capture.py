"""Frame capture service implementation for Camera Module v2."""

import logging
import time
from typing import Optional, Tuple, Any
import threading
from .interfaces import FrameCaptureServiceInterface
from .error_handler import global_error_handler, ErrorSeverity, with_error_handling, retry_on_error
from ..logging_config import get_logger, log_performance

# Handle camera imports gracefully
try:
    from picamera2 import Picamera2
    from picamera2.encoders import JpegEncoder
    from picamera2.outputs import FileOutput
    import numpy as np
    CAMERA_AVAILABLE = True
except ImportError:
    # Fallback for development without camera hardware
    CAMERA_AVAILABLE = False
    Picamera2 = None
    np = None

logger = get_logger("frame_capture")


class FrameCaptureService(FrameCaptureServiceInterface):
    """Camera frame capture service for Raspberry Pi Camera Module v2."""
    
    def __init__(self, resolution: Tuple[int, int] = (640, 480), framerate: float = 1.0):
        self.resolution = resolution
        self.framerate = framerate
        self.camera = None
        self._capturing = False
        self._latest_frame = None
        self._frame_lock = threading.Lock()
        self._capture_thread = None
        
        # Error handling and recovery
        self.error_count = 0
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        self.last_successful_capture = None
        self.recovery_mode = False
        
        # Register with error handler
        global_error_handler.register_component("frame_capture", max_recovery_attempts=5)
        global_error_handler.register_recovery_strategy("CameraInitError", self._recover_camera_init)
        global_error_handler.register_recovery_strategy("CaptureError", self._recover_capture_error)
        
        logger.info("Frame capture service initialized", extra={
            'context': {
                'resolution': f"{resolution[0]}x{resolution[1]}",
                'framerate': framerate,
                'camera_available': CAMERA_AVAILABLE
            }
        })
        
        logger.info(f"FrameCaptureService initialized - Resolution: {resolution}, FPS: {framerate}")
    
    def _recover_camera_init(self, error_record) -> bool:
        """Recover from camera initialization errors."""
        logger.info("Attempting camera initialization recovery")
        
        try:
            # Clean up existing camera instance
            if self.camera:
                try:
                    self.camera.close()
                except:
                    pass
                self.camera = None
            
            # Wait for hardware to stabilize
            time.sleep(3)
            
            # Try to reinitialize camera
            if CAMERA_AVAILABLE:
                self.camera = Picamera2()
                config = self.camera.create_still_configuration(
                    main={"size": self.resolution}
                )
                self.camera.configure(config)
                self.camera.start()
                
                logger.info("Camera initialization recovery successful")
                self.recovery_mode = False
                self.consecutive_errors = 0
                return True
            else:
                logger.warning("Camera hardware not available - entering mock mode")
                self.recovery_mode = True
                return True
                
        except Exception as e:
            logger.error(f"Camera initialization recovery failed: {e}")
            self.recovery_mode = True
            return False
    
    def _recover_capture_error(self, error_record) -> bool:
        """Recover from frame capture errors."""
        logger.info("Attempting capture error recovery")
        
        try:
            # Stop current capture
            if self._capturing:
                self._capturing = False
                if self._capture_thread:
                    self._capture_thread.join(timeout=2)
            
            # Wait for camera to stabilize
            time.sleep(2)
            
            # Restart capture if camera is available
            if self.camera and not self.recovery_mode:
                self._start_capture_thread()
                logger.info("Capture error recovery successful")
                self.consecutive_errors = 0
                return True
            else:
                logger.warning("Entering recovery mode - using mock frames")
                self.recovery_mode = True
                self._start_capture_thread()
                return True
                
        except Exception as e:
            logger.error(f"Capture error recovery failed: {e}")
            self.recovery_mode = True
            return False
        

    
    def get_frame(self) -> Optional[Any]:
        """Get the latest frame from camera."""
        with self._frame_lock:
            return self._latest_frame.copy() if self._latest_frame is not None else None
    
    def stop_capture(self) -> None:
        """Stop camera capture."""
        self._capturing = False
        
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=5.0)
            
        if self.camera:
            try:
                self.camera.stop()
                self.camera.close()
                self.camera = None
                logger.info("Camera capture stopped")
            except Exception as e:
                logger.error(f"Error stopping camera: {e}")
    
    def is_camera_available(self) -> bool:
        """Check if camera is available."""
        if not CAMERA_AVAILABLE:
            return False
            
        try:
            if self.camera is None:
                # Try to initialize camera briefly to test availability
                test_camera = Picamera2()
                test_camera.close()
                return True
            return True
        except Exception as e:
            logger.error(f"Camera availability check failed: {e}")
            return False
    

    
    def _start_mock_capture(self) -> None:
        """Start mock capture for development without camera hardware."""
        self._capturing = True
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()
        logger.info("Mock camera capture started")
    
    def _generate_mock_frame(self) -> None:
        """Generate a mock frame for development."""
        try:
            import numpy as np
            # Create a simple test pattern
            frame = np.zeros((self.resolution[1], self.resolution[0], 3), dtype=np.uint8)
            
            # Add some pattern to make it visually distinct
            frame[::20, :] = [100, 100, 100]  # Horizontal lines
            frame[:, ::20] = [100, 100, 100]  # Vertical lines
            
            # Add timestamp text area
            frame[10:50, 10:200] = [50, 50, 50]
            
            with self._frame_lock:
                self._latest_frame = frame
                
        except ImportError:
            # If numpy isn't available, create a simple placeholder
            with self._frame_lock:
                self._latest_frame = [[0, 0, 0] for _ in range(self.resolution[0] * self.resolution[1])]
    
    def set_resolution(self, resolution: Tuple[int, int]) -> None:
        """Change camera resolution (requires restart)."""
        if resolution != self.resolution:
            self.resolution = resolution
            if self._capturing:
                logger.info(f"Resolution changed to {resolution} - restart required")
    
    def set_framerate(self, framerate: float) -> None:
        """Change target framerate."""
        self.framerate = max(0.1, min(30.0, framerate))  # Clamp to reasonable range
        logger.info(f"Framerate set to {self.framerate} FPS")
    
    def get_camera_info(self) -> dict:
        """Get camera information and status."""
        return {
            "available": self.is_camera_available(),
            "capturing": self._capturing,
            "resolution": self.resolution,
            "framerate": self.framerate,
            "hardware_available": CAMERA_AVAILABLE,
            "latest_frame_available": self._latest_frame is not None,
            "error_count": self.error_count,
            "consecutive_errors": self.consecutive_errors,
            "recovery_mode": self.recovery_mode,
            "last_successful_capture": self.last_successful_capture.isoformat() if self.last_successful_capture else None
        }
    
    def _recover_camera_init(self, error_record) -> bool:
        """Recover from camera initialization errors."""
        logger.info("Attempting camera initialization recovery")
        
        try:
            # Clean up existing camera instance
            if self.camera:
                try:
                    self.camera.stop()
                    self.camera.close()
                except:
                    pass
                self.camera = None
            
            # Wait for hardware to stabilize
            time.sleep(3)
            
            # Try to reinitialize
            if CAMERA_AVAILABLE:
                self.camera = Picamera2()
                config = self.camera.create_still_configuration(
                    main={"size": self.resolution, "format": "RGB888"}
                )
                self.camera.configure(config)
                self.camera.start()
                time.sleep(2)
                
                logger.info("Camera initialization recovery successful")
                self.consecutive_errors = 0
                self.recovery_mode = False
                return True
            else:
                # Fall back to mock mode
                logger.warning("Camera hardware not available - falling back to mock mode")
                self.recovery_mode = True
                return True
                
        except Exception as e:
            logger.error(f"Camera initialization recovery failed: {e}")
            self.recovery_mode = True
            return False
    
    def _recover_capture_error(self, error_record) -> bool:
        """Recover from frame capture errors."""
        logger.info("Attempting capture error recovery")
        
        try:
            # Brief pause to let hardware stabilize
            time.sleep(1)
            
            # Try a test capture
            if CAMERA_AVAILABLE and self.camera:
                test_frame = self.camera.capture_array()
                if test_frame is not None:
                    logger.info("Capture error recovery successful")
                    self.consecutive_errors = 0
                    return True
            
            # If hardware capture fails, enable recovery mode
            self.recovery_mode = True
            logger.warning("Capture recovery enabled mock mode")
            return True
            
        except Exception as e:
            logger.error(f"Capture error recovery failed: {e}")
            self.consecutive_errors += 1
            
            if self.consecutive_errors >= self.max_consecutive_errors:
                logger.critical("Maximum consecutive capture errors reached - enabling recovery mode")
                self.recovery_mode = True
                global_error_handler.trigger_graceful_degradation("Camera capture failures")
            
            return False
    
    @with_error_handling("frame_capture", ErrorSeverity.HIGH)
    def _capture_loop(self) -> None:
        """Main capture loop running in separate thread."""
        frame_interval = 1.0 / self.framerate
        
        while self._capturing:
            try:
                start_time = time.time()
                
                if CAMERA_AVAILABLE and self.camera and not self.recovery_mode:
                    # Capture frame from camera
                    frame = self.camera.capture_array()
                    
                    with self._frame_lock:
                        self._latest_frame = frame
                    
                    # Reset error counters on successful capture
                    if self.consecutive_errors > 0:
                        logger.info("Camera capture recovered")
                        self.consecutive_errors = 0
                    
                    self.last_successful_capture = time.time()
                    
                else:
                    # Mock frame for development or recovery mode
                    self._generate_mock_frame()
                
                # Maintain target framerate
                elapsed = time.time() - start_time
                sleep_time = max(0, frame_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                self.error_count += 1
                self.consecutive_errors += 1
                
                # Handle error through error handler
                global_error_handler.handle_error(
                    "frame_capture", 
                    e, 
                    ErrorSeverity.MEDIUM if self.consecutive_errors < 3 else ErrorSeverity.HIGH
                )
                
                # Brief pause before retry
                time.sleep(1.0)
    
    @retry_on_error(max_attempts=3, delay=1.0, exceptions=(Exception,))
    def start_capture(self) -> None:
        """Start camera capture with retry logic."""
        if not CAMERA_AVAILABLE:
            logger.warning("Camera hardware not available - using mock mode")
            self._start_mock_capture()
            return
            
        try:
            if self.camera is None:
                self.camera = Picamera2()
                
                # Configure camera
                config = self.camera.create_still_configuration(
                    main={"size": self.resolution, "format": "RGB888"}
                )
                self.camera.configure(config)
                
                # Start camera
                self.camera.start()
                time.sleep(2)  # Camera warmup time
                
            self._capturing = True
            self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._capture_thread.start()
            
            logger.info(f"Camera capture started at {self.resolution} resolution, {self.framerate} FPS")
            self.consecutive_errors = 0
            
        except Exception as e:
            logger.error(f"Failed to start camera capture: {e}")
            self._capturing = False
            
            # Handle error through error handler
            global_error_handler.handle_error("frame_capture", e, ErrorSeverity.HIGH)
            raise