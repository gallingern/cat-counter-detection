"""Main detection pipeline that integrates all core services."""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from .services.frame_capture import FrameCaptureService
from .services.enhanced_detection_engine import EnhancedCatDetectionEngine
from .services.detection_validator import DetectionValidator
from .services.storage_service import StorageService
from .services.notification_service import NotificationService, NotificationConfig
from .services.performance_optimizer import PerformanceOptimizer
from .services.performance_profiler import PerformanceProfiler
from .services.error_handler import global_error_handler, ErrorSeverity, with_error_handling, retry_on_error
from .services.health_checker import HealthChecker
from .config_manager import ConfigManager
from .models.detection import ValidDetection
from .logging_config import get_logger, log_performance

logger = get_logger("detection_pipeline")


class DetectionPipeline:
    """Main detection pipeline that orchestrates all services."""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize detection pipeline with all services."""
        self.config_manager = config_manager or ConfigManager()
        self.config = self.config_manager.get_config()
        
        # Initialize error handling and health monitoring
        self.error_handler = global_error_handler
        self.health_checker = HealthChecker(self.error_handler)
        
        # Register pipeline with error handler
        self.error_handler.register_component("detection_pipeline", max_recovery_attempts=3)
        
        # Initialize services with error handling
        try:
            self.frame_capture = FrameCaptureService(
                resolution=(640, 480),
                framerate=self.config.target_fps
            )
            
            self.detection_engine = EnhancedCatDetectionEngine()
            
            self.detection_validator = DetectionValidator(
                confidence_threshold=self.config.confidence_threshold,
                counter_roi=self.config.detection_roi,
                temporal_consistency_frames=2
            )
            
            self.storage_service = StorageService(
                image_quality=self.config.image_quality,
                max_storage_days=self.config.max_storage_days
            )
            
            # Configure notification service
            notification_config = NotificationConfig(
                push_enabled=self.config.push_notifications_enabled,
                email_enabled=self.config.email_notifications_enabled,
                cooldown_minutes=self.config.notification_cooldown_minutes
            )
            self.notification_service = NotificationService(notification_config)
            
            # Initialize performance optimization components
            self.performance_optimizer = PerformanceOptimizer(self.config)
            self.performance_profiler = PerformanceProfiler()
            
        except Exception as e:
            self.error_handler.handle_error("detection_pipeline", e, ErrorSeverity.CRITICAL)
            raise
        
        # Pipeline state
        self.running = False
        self.pipeline_thread = None
        self.last_detection_time = None
        self.detection_count = 0
        self.error_count = 0
        self.consecutive_errors = 0
        self.max_consecutive_errors = 10
        
        # Performance monitoring
        self.frame_count = 0
        self.start_time = None
        self.last_fps_calculation = None
        self.current_fps = 0.0
        self.last_frame_time = 0.0
        self.last_detection_time_ms = 0.0
        
        # Health monitoring
        self._register_health_checks()
        
        logger.info("Detection pipeline initialized with comprehensive error handling")
        log_performance("Pipeline initialization completed", {
            "services_initialized": 6,
            "error_handling_enabled": True,
            "health_monitoring_enabled": True
        })
    
    def _register_health_checks(self) -> None:
        """Register health checks for all pipeline components."""
        try:
            # Register health check for frame capture
            self.health_checker.register_component_check(
                "frame_capture",
                lambda: self.frame_capture.is_capturing() if hasattr(self.frame_capture, 'is_capturing') else True,
                check_interval=30.0,
                timeout=5.0,
                max_failures=3
            )
            
            # Register health check for detection engine
            self.health_checker.register_component_check(
                "detection_engine", 
                lambda: hasattr(self.detection_engine, 'model_loaded') and self.detection_engine.model_loaded,
                check_interval=60.0,
                timeout=10.0,
                max_failures=2
            )
            
            # Register health check for storage service
            self.health_checker.register_component_check(
                "storage_service",
                lambda: self.storage_service.is_healthy() if hasattr(self.storage_service, 'is_healthy') else True,
                check_interval=45.0,
                timeout=5.0,
                max_failures=3
            )
            
            # Register health check for notification service
            self.health_checker.register_component_check(
                "notification_service",
                lambda: self.notification_service.is_healthy() if hasattr(self.notification_service, 'is_healthy') else True,
                check_interval=60.0,
                timeout=10.0,
                max_failures=5
            )
            
            # Register health check for pipeline itself
            self.health_checker.register_component_check(
                "pipeline_health",
                self._check_pipeline_health,
                check_interval=30.0,
                timeout=5.0,
                max_failures=3
            )
            
            logger.info("Health checks registered for all pipeline components")
            
        except Exception as e:
            self.error_handler.handle_error("detection_pipeline", e, ErrorSeverity.MEDIUM)
    
    def _check_pipeline_health(self) -> bool:
        """Check overall pipeline health."""
        try:
            # Check if pipeline is running when it should be
            if not self.running:
                return False
            
            # Check error rate
            if self.consecutive_errors >= self.max_consecutive_errors:
                return False
            
            # Check if we've had recent activity
            if self.last_detection_time:
                time_since_last = (datetime.now() - self.last_detection_time).total_seconds()
                # If no detections for more than 1 hour, that's still healthy (cats might not be around)
                # But if we haven't processed any frames in 5 minutes, that's concerning
                if hasattr(self, 'last_frame_processed') and self.last_frame_processed:
                    time_since_frame = (datetime.now() - self.last_frame_processed).total_seconds()
                    if time_since_frame > 300:  # 5 minutes
                        return False
            
            return True
            
        except Exception:
            return False
    
    def start(self) -> bool:
        """Start the detection pipeline."""
        if self.running:
            logger.warning("Pipeline is already running")
            return False
        
        try:
            # Load detection model
            self._load_detection_model()
            
            # Start frame capture
            self.frame_capture.start_capture()
            
            # Start performance monitoring
            self.performance_optimizer.start_monitoring()
            
            # Optimize detection engine for current performance level
            self.performance_optimizer.optimize_detection_engine_settings(self.detection_engine)
            
            # Start pipeline processing
            self.running = True
            self.start_time = datetime.now()
            self.last_fps_calculation = self.start_time
            self.pipeline_thread = threading.Thread(target=self._pipeline_loop, daemon=True)
            self.pipeline_thread.start()
            
            logger.info("Detection pipeline started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start detection pipeline: {e}")
            self.stop()
            return False
    
    def stop(self) -> None:
        """Stop the detection pipeline."""
        logger.info("Stopping detection pipeline...")
        
        self.running = False
        
        # Stop services
        if self.frame_capture:
            self.frame_capture.stop_capture()
        
        if self.notification_service:
            self.notification_service.stop_processing()
        
        # Stop performance monitoring
        if self.performance_optimizer:
            self.performance_optimizer.stop_monitoring()
        
        # Wait for pipeline thread to finish
        if self.pipeline_thread and self.pipeline_thread.is_alive():
            self.pipeline_thread.join(timeout=5.0)
        
        logger.info("Detection pipeline stopped")
    
    def _pipeline_loop(self) -> None:
        """Main pipeline processing loop."""
        logger.info("Pipeline processing loop started")
        
        while self.running:
            try:
                # Check if monitoring is enabled and within schedule
                if not self._is_monitoring_active():
                    time.sleep(1.0)
                    continue
                
                # Get frame from camera
                frame = self.frame_capture.get_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue
                
                # Process frame through detection pipeline
                self._process_frame(frame)
                
                # Update performance metrics
                self._update_performance_metrics()
                
                # Brief pause to maintain target FPS
                time.sleep(1.0 / self.config.target_fps)
                
            except Exception as e:
                logger.error(f"Error in pipeline loop: {e}")
                self.error_count += 1
                time.sleep(1.0)  # Brief pause on error
        
        logger.info("Pipeline processing loop ended")
    
    def _process_frame(self, frame: Any) -> None:
        """Process a single frame through the detection pipeline."""
        frame_start_time = time.time()
        
        try:
            # Step 0: Apply performance optimizations to frame
            optimized_frame = self.performance_optimizer.optimize_frame_processing(frame, self.frame_count)
            
            # If frame was skipped due to optimization, return early
            if optimized_frame is None:
                return
            
            # Step 1: Detect cats in frame
            detection_start_time = time.time()
            raw_detections = self.detection_engine.detect_cats(optimized_frame)
            detection_time_ms = (time.time() - detection_start_time) * 1000
            
            if not raw_detections:
                # Update performance metrics even for frames with no detections
                frame_processing_time_ms = (time.time() - frame_start_time) * 1000
                self.performance_optimizer.update_pipeline_metrics(
                    fps=self.current_fps,
                    processing_time_ms=frame_processing_time_ms,
                    detection_time_ms=detection_time_ms,
                    total_detections=self.detection_count,
                    error_count=self.error_count
                )
                return
            
            # Step 2: Validate detections
            valid_detections = self.detection_validator.validate_detections(raw_detections)
            
            if not valid_detections:
                # Update performance metrics
                frame_processing_time_ms = (time.time() - frame_start_time) * 1000
                self.performance_optimizer.update_pipeline_metrics(
                    fps=self.current_fps,
                    processing_time_ms=frame_processing_time_ms,
                    detection_time_ms=detection_time_ms,
                    total_detections=self.detection_count,
                    error_count=self.error_count
                )
                return
            
            # Step 3: Count cats
            cat_count = self.detection_validator.count_cats(valid_detections)
            
            if cat_count == 0:
                # Update performance metrics
                frame_processing_time_ms = (time.time() - frame_start_time) * 1000
                self.performance_optimizer.update_pipeline_metrics(
                    fps=self.current_fps,
                    processing_time_ms=frame_processing_time_ms,
                    detection_time_ms=detection_time_ms,
                    total_detections=self.detection_count,
                    error_count=self.error_count
                )
                return
            
            logger.info(f"Detected {cat_count} cat(s) on counter")
            
            # Step 4: Process each valid detection
            for detection in valid_detections:
                self._handle_valid_detection(detection, frame)  # Use original frame for saving
            
            # Update detection statistics
            self.detection_count += len(valid_detections)
            self.last_detection_time = datetime.now()
            
            # Update performance metrics
            frame_processing_time_ms = (time.time() - frame_start_time) * 1000
            self.performance_optimizer.update_pipeline_metrics(
                fps=self.current_fps,
                processing_time_ms=frame_processing_time_ms,
                detection_time_ms=detection_time_ms,
                total_detections=self.detection_count,
                error_count=self.error_count
            )
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            self.error_count += 1
            
            # Update performance metrics with error
            frame_processing_time_ms = (time.time() - frame_start_time) * 1000
            self.performance_optimizer.update_pipeline_metrics(
                fps=self.current_fps,
                processing_time_ms=frame_processing_time_ms,
                detection_time_ms=0.0,
                total_detections=self.detection_count,
                error_count=self.error_count
            )
    
    def _handle_valid_detection(self, detection: ValidDetection, frame: Any) -> None:
        """Handle a valid detection by saving and notifying."""
        try:
            # Step 1: Save detection and image
            image_path = self.storage_service.save_detection(detection, frame)
            
            # Step 2: Send notifications
            self._send_notifications(detection, image_path)
            
            logger.info(f"Processed detection: {detection.cat_count} cat(s), "
                       f"confidence: {detection.validated_confidence:.2f}")
            
        except Exception as e:
            logger.error(f"Error handling detection: {e}")
    
    def _send_notifications(self, detection: ValidDetection, image_path: str) -> None:
        """Send notifications for a detection."""
        try:
            # Create notification message
            cat_word = "cat" if detection.cat_count == 1 else "cats"
            message = (f"Alert! {detection.cat_count} {cat_word} detected on kitchen counter "
                      f"at {detection.timestamp.strftime('%H:%M:%S')} "
                      f"(confidence: {detection.validated_confidence:.1%})")
            
            # Send push notification
            if self.config.push_notifications_enabled:
                success = self.notification_service.send_push_notification(message, image_path)
                if not success:
                    # Queue for retry if immediate send fails
                    self.notification_service.queue_notification("push", message, image_path)
            
            # Send email notification
            if self.config.email_notifications_enabled:
                email_subject = f"Cat Counter Alert - {detection.cat_count} {cat_word} detected"
                success = self.notification_service.send_email(email_subject, message, image_path)
                if not success:
                    # Queue for retry if immediate send fails
                    self.notification_service.queue_notification("email", message, image_path)
            
        except Exception as e:
            logger.error(f"Error sending notifications: {e}")
    
    def _is_monitoring_active(self) -> bool:
        """Check if monitoring is currently active based on schedule."""
        if not self.config.monitoring_enabled:
            return False
        
        current_hour = datetime.now().hour
        start_hour = self.config.monitoring_start_hour
        end_hour = self.config.monitoring_end_hour
        
        # Handle case where monitoring spans midnight
        if start_hour <= end_hour:
            return start_hour <= current_hour <= end_hour
        else:
            return current_hour >= start_hour or current_hour <= end_hour
    
    def _load_detection_model(self) -> None:
        """Load the detection model with enhanced engine support."""
        try:
            # Try to load MobileNetV2 model first, then fallback to OpenCV
            model_paths = [
                "models/mobilenet_v2_coco.tflite",
                "models/cat_detection_mobilenet.tflite",
                "models/haarcascade_frontalcatface.xml",
                "models/cat_detection_model.xml",
                # Will fall back to built-in cascades if these don't exist
            ]
            
            model_loaded = False
            for model_path in model_paths:
                try:
                    self.detection_engine.load_model(model_path)
                    if (hasattr(self.detection_engine, 'primary_model_loaded') and 
                        self.detection_engine.primary_model_loaded) or \
                       (hasattr(self.detection_engine, 'fallback_model_loaded') and 
                        self.detection_engine.fallback_model_loaded):
                        logger.info(f"Loaded detection model: {model_path}")
                        model_loaded = True
                        break
                except Exception as e:
                    logger.debug(f"Failed to load model {model_path}: {e}")
            
            if not model_loaded:
                logger.warning("No specific model found, using default fallback")
                # Try to load with empty path to trigger fallback
                self.detection_engine.load_model("")
            
            # Configure detection engine
            self.detection_engine.set_confidence_threshold(self.config.confidence_threshold)
            self.detection_engine.set_roi(self.config.detection_roi)
            
            # Log current model info
            if hasattr(self.detection_engine, 'get_current_model'):
                current_model = self.detection_engine.get_current_model()
                logger.info(f"Active detection model: {current_model}")
            
        except Exception as e:
            logger.error(f"Error loading detection model: {e}")
            raise
    
    def _update_performance_metrics(self) -> None:
        """Update performance metrics."""
        self.frame_count += 1
        
        # Calculate FPS every 10 frames
        if self.frame_count % 10 == 0:
            current_time = datetime.now()
            if self.last_fps_calculation:
                time_diff = (current_time - self.last_fps_calculation).total_seconds()
                if time_diff > 0:
                    self.current_fps = 10.0 / time_diff
            self.last_fps_calculation = current_time
    
    def get_status(self) -> Dict[str, Any]:
        """Get current pipeline status and statistics."""
        uptime = None
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "running": self.running,
            "monitoring_active": self._is_monitoring_active(),
            "uptime_seconds": uptime,
            "frame_count": self.frame_count,
            "current_fps": self.current_fps,
            "detection_count": self.detection_count,
            "error_count": self.error_count,
            "last_detection": self.last_detection_time.isoformat() if self.last_detection_time else None,
            "services": {
                "frame_capture": self.frame_capture.get_camera_info(),
                "detection_engine": self.detection_engine.get_model_info() if hasattr(self.detection_engine, 'get_model_info') else self.detection_engine.get_detection_info(),
                "detection_validator": self.detection_validator.get_validation_stats(),
                "storage_service": self.storage_service.get_storage_info(),
                "notification_service": self.notification_service.get_notification_stats()
            }
        }
    
    def update_configuration(self, **kwargs) -> None:
        """Update pipeline configuration and apply to services."""
        try:
            # Update configuration
            self.config_manager.update_config(**kwargs)
            self.config = self.config_manager.get_config()
            
            # Apply configuration changes to services
            if 'confidence_threshold' in kwargs:
                self.detection_engine.set_confidence_threshold(self.config.confidence_threshold)
                self.detection_validator.set_confidence_threshold(self.config.confidence_threshold)
            
            if 'detection_roi' in kwargs:
                self.detection_engine.set_roi(self.config.detection_roi)
                self.detection_validator.set_counter_roi(self.config.detection_roi)
            
            if 'target_fps' in kwargs:
                self.frame_capture.set_framerate(self.config.target_fps)
            
            # Update notification service configuration
            notification_updates = {}
            if 'push_notifications_enabled' in kwargs:
                notification_updates['push_enabled'] = self.config.push_notifications_enabled
            if 'email_notifications_enabled' in kwargs:
                notification_updates['email_enabled'] = self.config.email_notifications_enabled
            if 'notification_cooldown_minutes' in kwargs:
                notification_updates['cooldown_minutes'] = self.config.notification_cooldown_minutes
            
            if notification_updates:
                self.notification_service.update_config(**notification_updates)
            
            logger.info(f"Configuration updated: {kwargs}")
            
        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
    
    def trigger_test_detection(self) -> bool:
        """Trigger a test detection for testing purposes."""
        try:
            # Create a mock detection
            from .models.detection import ValidDetection, BoundingBox
            
            bbox = BoundingBox(x=200, y=200, width=100, height=100, confidence=0.9)
            test_detection = ValidDetection(
                timestamp=datetime.now(),
                bounding_boxes=[bbox],
                frame_width=640,
                frame_height=480,
                raw_confidence=0.9,
                cat_count=1,
                is_on_counter=True,
                validated_confidence=0.95
            )
            
            # Create a mock frame
            mock_frame = [[0 for _ in range(640)] for _ in range(480)]
            
            # Process the test detection
            self._handle_valid_detection(test_detection, mock_frame)
            
            logger.info("Test detection triggered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error triggering test detection: {e}")
            return False
    
    def cleanup_old_data(self) -> None:
        """Trigger cleanup of old data."""
        try:
            self.storage_service.cleanup_old_data()
            logger.info("Data cleanup completed")
        except Exception as e:
            logger.error(f"Error during data cleanup: {e}")
    
    def get_recent_detections(self, limit: int = 10) -> List[Any]:
        """Get recent detections from storage."""
        try:
            return self.storage_service.get_recent_detections(limit)
        except Exception as e:
            logger.error(f"Error getting recent detections: {e}")
            return []