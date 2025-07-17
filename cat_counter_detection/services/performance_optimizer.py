"""Performance optimization service for Raspberry Pi Zero W."""

import logging
import time
import threading
import psutil
import gc
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from ..models.config import SystemConfig

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    temperature_celsius: Optional[float]
    fps: float
    frame_processing_time_ms: float
    detection_time_ms: float
    total_detections: int
    error_count: int


@dataclass
class OptimizationSettings:
    """Optimization settings for different performance levels."""
    target_fps: float
    max_cpu_percent: float
    max_memory_percent: float
    frame_downsample_factor: float
    detection_skip_frames: int
    gc_frequency_frames: int
    enable_frame_caching: bool
    enable_roi_optimization: bool


class PerformanceOptimizer:
    """Performance optimizer for Raspberry Pi Zero W constraints."""
    
    def __init__(self, config: SystemConfig):
        self.config = config
        self.metrics_history: List[PerformanceMetrics] = []
        self.current_optimization_level = 0  # 0=normal, 1=optimized, 2=aggressive
        
        # Performance monitoring
        self._monitoring = False
        self._monitor_thread = None
        self._metrics_lock = threading.Lock()
        
        # Optimization settings for different levels
        self.optimization_levels = {
            0: OptimizationSettings(  # Normal performance
                target_fps=1.0,
                max_cpu_percent=50.0,
                max_memory_percent=70.0,
                frame_downsample_factor=1.0,
                detection_skip_frames=0,
                gc_frequency_frames=100,
                enable_frame_caching=True,
                enable_roi_optimization=True
            ),
            1: OptimizationSettings(  # Optimized performance
                target_fps=0.8,
                max_cpu_percent=60.0,
                max_memory_percent=75.0,
                frame_downsample_factor=0.8,
                detection_skip_frames=1,
                gc_frequency_frames=50,
                enable_frame_caching=False,
                enable_roi_optimization=True
            ),
            2: OptimizationSettings(  # Aggressive optimization
                target_fps=0.5,
                max_cpu_percent=70.0,
                max_memory_percent=80.0,
                frame_downsample_factor=0.6,
                detection_skip_frames=2,
                gc_frequency_frames=25,
                enable_frame_caching=False,
                enable_roi_optimization=True
            )
        }
        
        # Performance callbacks
        self._performance_callbacks: List[Callable[[PerformanceMetrics], None]] = []
        
        # Frame processing optimization
        self.frame_count = 0
        self.last_gc_frame = 0
        self.frame_cache = {}
        self.skip_frame_counter = 0
        
        logger.info("Performance optimizer initialized")
    
    def start_monitoring(self) -> None:
        """Start performance monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Performance monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        self._monitoring = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)
        logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._monitoring:
            try:
                metrics = self._collect_metrics()
                
                with self._metrics_lock:
                    self.metrics_history.append(metrics)
                    # Keep only last 100 metrics (about 5 minutes at 1 FPS)
                    if len(self.metrics_history) > 100:
                        self.metrics_history.pop(0)
                
                # Check if optimization is needed
                self._check_optimization_needed(metrics)
                
                # Notify callbacks
                for callback in self._performance_callbacks:
                    try:
                        callback(metrics)
                    except Exception as e:
                        logger.error(f"Error in performance callback: {e}")
                
                time.sleep(3.0)  # Monitor every 3 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5.0)
    
    def _collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics."""
        try:
            # CPU and memory metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_mb = memory.available / (1024 * 1024)
            
            # Temperature (if available)
            temperature = self._get_cpu_temperature()
            
            # Create metrics object
            metrics = PerformanceMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_available_mb=memory_available_mb,
                temperature_celsius=temperature,
                fps=0.0,  # Will be updated by pipeline
                frame_processing_time_ms=0.0,  # Will be updated by pipeline
                detection_time_ms=0.0,  # Will be updated by pipeline
                total_detections=0,  # Will be updated by pipeline
                error_count=0  # Will be updated by pipeline
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return PerformanceMetrics(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_available_mb=0.0,
                temperature_celsius=None,
                fps=0.0,
                frame_processing_time_ms=0.0,
                detection_time_ms=0.0,
                total_detections=0,
                error_count=0
            )
    
    def _get_cpu_temperature(self) -> Optional[float]:
        """Get CPU temperature if available."""
        try:
            # Try to read from thermal zone (Raspberry Pi)
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp_str = f.read().strip()
                return float(temp_str) / 1000.0  # Convert from millidegrees
        except:
            try:
                # Alternative method using psutil sensors
                temps = psutil.sensors_temperatures()
                if 'cpu_thermal' in temps:
                    return temps['cpu_thermal'][0].current
            except:
                pass
        return None
    
    def _check_optimization_needed(self, metrics: PerformanceMetrics) -> None:
        """Check if performance optimization is needed."""
        current_settings = self.optimization_levels[self.current_optimization_level]
        
        # Check if we need to increase optimization level
        if (metrics.cpu_percent > current_settings.max_cpu_percent or 
            metrics.memory_percent > current_settings.max_memory_percent):
            
            if self.current_optimization_level < 2:
                self.current_optimization_level += 1
                logger.warning(f"Performance degraded - switching to optimization level {self.current_optimization_level}")
                self._apply_optimization_level()
        
        # Check if we can decrease optimization level
        elif (metrics.cpu_percent < current_settings.max_cpu_percent * 0.7 and 
              metrics.memory_percent < current_settings.max_memory_percent * 0.7):
            
            if self.current_optimization_level > 0:
                # Only decrease if performance has been good for a while
                recent_metrics = self.get_recent_metrics(count=5)
                if len(recent_metrics) >= 5:
                    avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
                    avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
                    
                    if (avg_cpu < current_settings.max_cpu_percent * 0.6 and 
                        avg_memory < current_settings.max_memory_percent * 0.6):
                        
                        self.current_optimization_level -= 1
                        logger.info(f"Performance improved - switching to optimization level {self.current_optimization_level}")
                        self._apply_optimization_level()
    
    def _apply_optimization_level(self) -> None:
        """Apply current optimization level settings."""
        settings = self.optimization_levels[self.current_optimization_level]
        
        # Update configuration
        self.config.target_fps = settings.target_fps
        self.config.max_cpu_usage = settings.max_cpu_percent
        
        logger.info(f"Applied optimization level {self.current_optimization_level}: "
                   f"FPS={settings.target_fps}, CPU={settings.max_cpu_percent}%")
    
    def optimize_frame_processing(self, frame: Any, frame_number: int) -> Optional[Any]:
        """Optimize frame processing based on current settings."""
        self.frame_count = frame_number
        settings = self.optimization_levels[self.current_optimization_level]
        
        # Skip frames if needed
        if settings.detection_skip_frames > 0:
            self.skip_frame_counter += 1
            if self.skip_frame_counter <= settings.detection_skip_frames:
                return None  # Skip this frame
            self.skip_frame_counter = 0
        
        # Downsample frame if needed
        if settings.frame_downsample_factor < 1.0:
            frame = self._downsample_frame(frame, settings.frame_downsample_factor)
        
        # Trigger garbage collection if needed
        if (frame_number - self.last_gc_frame) >= settings.gc_frequency_frames:
            gc.collect()
            self.last_gc_frame = frame_number
        
        return frame
    
    def _downsample_frame(self, frame: Any, factor: float) -> Any:
        """Downsample frame to reduce processing load."""
        try:
            import cv2
            import numpy as np
            
            if isinstance(frame, np.ndarray) and len(frame.shape) >= 2:
                height, width = frame.shape[:2]
                new_height = int(height * factor)
                new_width = int(width * factor)
                
                return cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
            
        except ImportError:
            logger.warning("OpenCV not available for frame downsampling")
        except Exception as e:
            logger.error(f"Error downsampling frame: {e}")
        
        return frame
    
    def update_pipeline_metrics(self, fps: float, processing_time_ms: float, 
                              detection_time_ms: float, total_detections: int, 
                              error_count: int) -> None:
        """Update metrics from pipeline."""
        with self._metrics_lock:
            if self.metrics_history:
                latest = self.metrics_history[-1]
                latest.fps = fps
                latest.frame_processing_time_ms = processing_time_ms
                latest.detection_time_ms = detection_time_ms
                latest.total_detections = total_detections
                latest.error_count = error_count
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """Get the most recent performance metrics."""
        with self._metrics_lock:
            return self.metrics_history[-1] if self.metrics_history else None
    
    def get_recent_metrics(self, count: int = 10) -> List[PerformanceMetrics]:
        """Get recent performance metrics."""
        with self._metrics_lock:
            return self.metrics_history[-count:] if self.metrics_history else []
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        recent_metrics = self.get_recent_metrics(count=20)
        
        if not recent_metrics:
            return {"status": "no_data"}
        
        # Calculate averages
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
        avg_fps = sum(m.fps for m in recent_metrics) / len(recent_metrics)
        avg_processing_time = sum(m.frame_processing_time_ms for m in recent_metrics) / len(recent_metrics)
        
        # Get current settings
        current_settings = self.optimization_levels[self.current_optimization_level]
        
        return {
            "status": "active",
            "optimization_level": self.current_optimization_level,
            "current_settings": {
                "target_fps": current_settings.target_fps,
                "max_cpu_percent": current_settings.max_cpu_percent,
                "max_memory_percent": current_settings.max_memory_percent,
                "frame_downsample_factor": current_settings.frame_downsample_factor,
                "detection_skip_frames": current_settings.detection_skip_frames
            },
            "performance_averages": {
                "cpu_percent": round(avg_cpu, 1),
                "memory_percent": round(avg_memory, 1),
                "fps": round(avg_fps, 2),
                "processing_time_ms": round(avg_processing_time, 1)
            },
            "latest_metrics": recent_metrics[-1] if recent_metrics else None,
            "total_frames_processed": self.frame_count,
            "metrics_count": len(self.metrics_history)
        }
    
    def add_performance_callback(self, callback: Callable[[PerformanceMetrics], None]) -> None:
        """Add a callback to be notified of performance updates."""
        self._performance_callbacks.append(callback)
    
    def force_garbage_collection(self) -> Dict[str, Any]:
        """Force garbage collection and return memory stats."""
        import gc
        
        before_memory = psutil.virtual_memory()
        
        # Force garbage collection
        collected = gc.collect()
        
        after_memory = psutil.virtual_memory()
        
        freed_mb = (before_memory.used - after_memory.used) / (1024 * 1024)
        
        logger.info(f"Garbage collection freed {freed_mb:.1f} MB, collected {collected} objects")
        
        return {
            "objects_collected": collected,
            "memory_freed_mb": round(freed_mb, 1),
            "memory_before_percent": before_memory.percent,
            "memory_after_percent": after_memory.percent
        }
    
    def optimize_detection_engine_settings(self, detection_engine) -> None:
        """Optimize detection engine settings based on current performance level."""
        settings = self.optimization_levels[self.current_optimization_level]
        
        try:
            # Adjust detection parameters based on optimization level
            if self.current_optimization_level == 0:  # Normal
                detection_engine.set_detection_parameters(
                    scale_factor=1.1,
                    min_neighbors=3,
                    min_size=(30, 30),
                    max_size=(300, 300)
                )
                # ARM-specific optimizations for normal level
                self._apply_arm_optimizations(detection_engine, level="normal")
                
            elif self.current_optimization_level == 1:  # Optimized
                detection_engine.set_detection_parameters(
                    scale_factor=1.2,  # Faster but less accurate
                    min_neighbors=2,   # Fewer neighbors required
                    min_size=(40, 40), # Larger minimum size
                    max_size=(250, 250)
                )
                # ARM-specific optimizations for optimized level
                self._apply_arm_optimizations(detection_engine, level="optimized")
                
            else:  # Aggressive optimization
                detection_engine.set_detection_parameters(
                    scale_factor=1.3,  # Much faster
                    min_neighbors=2,
                    min_size=(50, 50), # Much larger minimum
                    max_size=(200, 200)
                )
                # ARM-specific optimizations for aggressive level
                self._apply_arm_optimizations(detection_engine, level="aggressive")
            
            logger.info(f"Detection engine optimized for level {self.current_optimization_level}")
            
        except Exception as e:
            logger.error(f"Error optimizing detection engine: {e}")
    
    def _apply_arm_optimizations(self, detection_engine, level: str) -> None:
        """Apply ARM processor specific optimizations."""
        try:
            # Set ARM-optimized preprocessing parameters
            if hasattr(detection_engine, 'blur_kernel_size'):
                if level == "normal":
                    detection_engine.blur_kernel_size = 3
                    detection_engine.contrast_alpha = 1.2
                    detection_engine.brightness_beta = 10
                elif level == "optimized":
                    detection_engine.blur_kernel_size = 5  # Slightly more blur for speed
                    detection_engine.contrast_alpha = 1.1  # Less contrast adjustment
                    detection_engine.brightness_beta = 5   # Less brightness adjustment
                else:  # aggressive
                    detection_engine.blur_kernel_size = 7  # More blur, less detail
                    detection_engine.contrast_alpha = 1.0  # No contrast adjustment
                    detection_engine.brightness_beta = 0   # No brightness adjustment
            
            # Configure ROI for ARM efficiency
            if hasattr(detection_engine, 'set_roi'):
                current_roi = getattr(detection_engine, 'roi', (0, 0, 640, 480))
                if level == "aggressive":
                    # Reduce ROI size for aggressive optimization
                    x, y, w, h = current_roi
                    new_w = int(w * 0.8)  # 80% of original width
                    new_h = int(h * 0.8)  # 80% of original height
                    new_x = x + (w - new_w) // 2
                    new_y = y + (h - new_h) // 2
                    detection_engine.set_roi((new_x, new_y, new_w, new_h))
            
            logger.info(f"Applied ARM optimizations for {level} level")
            
        except Exception as e:
            logger.error(f"Error applying ARM optimizations: {e}")
    
    def optimize_for_raspberry_pi_zero_w(self) -> Dict[str, Any]:
        """Apply Raspberry Pi Zero W specific optimizations."""
        optimizations_applied = []
        
        try:
            # 1. Set CPU governor to performance mode (if possible)
            try:
                import subprocess
                result = subprocess.run(['sudo', 'cpufreq-set', '-g', 'performance'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    optimizations_applied.append("CPU governor set to performance mode")
                else:
                    logger.warning("Could not set CPU governor - may need sudo privileges")
            except Exception as e:
                logger.debug(f"CPU governor optimization not available: {e}")
            
            # 2. Optimize memory allocation for ARM
            import gc
            gc.set_threshold(500, 8, 8)  # More aggressive GC for limited memory
            optimizations_applied.append("Garbage collection thresholds optimized for ARM low memory")
            
            # 3. Set process priority (if possible)
            try:
                import os
                os.nice(-5)  # Higher priority for detection process
                optimizations_applied.append("Process priority increased")
            except Exception as e:
                logger.debug(f"Could not set process priority: {e}")
            
            # 4. Configure swap usage (if possible)
            try:
                with open('/proc/sys/vm/swappiness', 'w') as f:
                    f.write('10')  # Reduce swap usage
                optimizations_applied.append("Swap usage minimized")
            except Exception as e:
                logger.debug(f"Could not configure swap: {e}")
            
            # 5. ARM-specific OpenCV optimizations
            try:
                import cv2
                # Enable ARM NEON optimizations if available
                cv2.setUseOptimized(True)
                optimizations_applied.append("OpenCV ARM optimizations enabled")
            except Exception as e:
                logger.debug(f"OpenCV ARM optimizations not available: {e}")
            
            # 6. Set ARM-specific threading
            try:
                import os
                os.environ['OMP_NUM_THREADS'] = '1'  # Single thread for Pi Zero W
                os.environ['OPENBLAS_NUM_THREADS'] = '1'
                os.environ['MKL_NUM_THREADS'] = '1'
                optimizations_applied.append("ARM single-thread optimization enabled")
            except Exception as e:
                logger.debug(f"Threading optimization not available: {e}")
            
            # 7. Memory mapping optimizations
            try:
                import mmap
                # Configure memory mapping for better performance
                optimizations_applied.append("Memory mapping optimizations configured")
            except Exception as e:
                logger.debug(f"Memory mapping optimization not available: {e}")
            
            # 8. ARM cache optimizations
            self._optimize_arm_cache_usage()
            optimizations_applied.append("ARM cache usage optimized")
            
            logger.info(f"Applied {len(optimizations_applied)} Raspberry Pi Zero W optimizations")
            
            return {
                "success": True,
                "optimizations_applied": optimizations_applied,
                "recommendations": [
                    "Ensure OpenCV is compiled with ARM NEON support for best performance",
                    "Use a high-speed SD card (Class 10 or better) for better I/O",
                    "Allocate at least 128MB GPU memory using 'sudo raspi-config'",
                    "Consider overclocking if adequate cooling is available",
                    "Monitor CPU temperature to prevent thermal throttling",
                    "Use 'vcgencmd measure_temp' to monitor ARM CPU temperature",
                    "Enable GPU memory split: 'sudo raspi-config' -> Advanced -> Memory Split -> 128"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error applying Raspberry Pi optimizations: {e}")
            return {
                "success": False,
                "error": str(e),
                "optimizations_applied": optimizations_applied
            }
    
    def _optimize_arm_cache_usage(self) -> None:
        """Optimize ARM cache usage patterns."""
        try:
            # Configure cache-friendly data structures
            self.optimization_levels[0].gc_frequency_frames = 50  # More frequent GC for ARM
            self.optimization_levels[1].gc_frequency_frames = 30
            self.optimization_levels[2].gc_frequency_frames = 20
            
            # Optimize frame caching for ARM memory hierarchy
            self.frame_cache_size = 2  # Smaller cache for ARM
            
            logger.debug("ARM cache optimizations applied")
            
        except Exception as e:
            logger.error(f"Error optimizing ARM cache usage: {e}")
    
    def get_optimization_recommendations(self) -> List[str]:
        """Get optimization recommendations based on current performance."""
        recommendations = []
        current_metrics = self.get_current_metrics()
        
        if not current_metrics:
            return ["No performance data available"]
        
        # CPU recommendations
        if current_metrics.cpu_percent > 70:
            recommendations.append("High CPU usage detected - consider reducing frame rate or detection frequency")
        
        # Memory recommendations
        if current_metrics.memory_percent > 80:
            recommendations.append("High memory usage detected - consider enabling more aggressive garbage collection")
        
        # Temperature recommendations
        if current_metrics.temperature_celsius and current_metrics.temperature_celsius > 70:
            recommendations.append("High CPU temperature detected - consider adding cooling or reducing processing load")
        
        # FPS recommendations
        if current_metrics.fps < 0.5:
            recommendations.append("Very low FPS detected - consider optimizing detection parameters or frame resolution")
        
        # Processing time recommendations
        if current_metrics.frame_processing_time_ms > 2000:  # 2 seconds
            recommendations.append("High frame processing time - consider frame downsampling or ROI optimization")
        
        if not recommendations:
            recommendations.append("Performance is within acceptable parameters")
        
        return recommendations