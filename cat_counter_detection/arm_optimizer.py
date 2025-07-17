#!/usr/bin/env python3
"""ARM processor optimization script for Raspberry Pi Zero W."""

import logging
import os
import sys
import time
from typing import Dict, Any, List
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cat_counter_detection.services.performance_optimizer import PerformanceOptimizer
from cat_counter_detection.services.detection_engine import CatDetectionEngine
from cat_counter_detection.services.system_monitor import SystemMonitor
from cat_counter_detection.config_manager import ConfigManager

# Handle optional imports
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    cv2 = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ARMOptimizer:
    """Comprehensive ARM processor optimization for Raspberry Pi Zero W."""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()
        self.performance_optimizer = PerformanceOptimizer(self.config)
        self.detection_engine = CatDetectionEngine()
        self.system_monitor = SystemMonitor()
        
        # Optimization results
        self.optimization_results: Dict[str, Any] = {}
        
        logger.info("ARM Optimizer initialized for Raspberry Pi Zero W")
    
    def apply_all_optimizations(self) -> Dict[str, Any]:
        """Apply all ARM-specific optimizations."""
        logger.info("Starting comprehensive ARM optimization...")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "system_info": self._get_system_info(),
            "optimizations": {},
            "performance_before": {},
            "performance_after": {},
            "recommendations": []
        }
        
        try:
            # Step 1: Collect baseline performance
            logger.info("Step 1: Collecting baseline performance metrics...")
            results["performance_before"] = self._collect_performance_metrics()
            
            # Step 2: Apply system-level optimizations
            logger.info("Step 2: Applying system-level ARM optimizations...")
            results["optimizations"]["system"] = self._apply_system_optimizations()
            
            # Step 3: Apply OpenCV optimizations
            logger.info("Step 3: Applying OpenCV ARM optimizations...")
            results["optimizations"]["opencv"] = self._apply_opencv_optimizations()
            
            # Step 4: Apply detection engine optimizations
            logger.info("Step 4: Applying detection engine optimizations...")
            results["optimizations"]["detection"] = self._apply_detection_optimizations()
            
            # Step 5: Apply memory optimizations
            logger.info("Step 5: Applying memory optimizations...")
            results["optimizations"]["memory"] = self._apply_memory_optimizations()
            
            # Step 6: Apply performance optimizer settings
            logger.info("Step 6: Applying performance optimizer settings...")
            results["optimizations"]["performance"] = self._apply_performance_optimizations()
            
            # Step 7: Collect post-optimization performance
            logger.info("Step 7: Collecting post-optimization performance metrics...")
            time.sleep(5)  # Allow optimizations to take effect
            results["performance_after"] = self._collect_performance_metrics()
            
            # Step 8: Generate recommendations
            logger.info("Step 8: Generating optimization recommendations...")
            results["recommendations"] = self._generate_recommendations(results)
            
            logger.info("ARM optimization completed successfully")
            
        except Exception as e:
            logger.error(f"Error during ARM optimization: {e}")
            results["error"] = str(e)
        
        self.optimization_results = results
        return results
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for ARM optimization."""
        info = {
            "timestamp": datetime.now().isoformat(),
            "psutil_available": PSUTIL_AVAILABLE,
            "opencv_available": OPENCV_AVAILABLE,
            "platform": sys.platform
        }
        
        if PSUTIL_AVAILABLE:
            try:
                info.update({
                    "cpu_count": psutil.cpu_count(),
                    "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
                    "memory_total_mb": psutil.virtual_memory().total / (1024 * 1024),
                    "memory_available_mb": psutil.virtual_memory().available / (1024 * 1024),
                    "disk_usage_percent": psutil.disk_usage('/').percent,
                    "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
                })
            except Exception as e:
                logger.warning(f"Error getting detailed system info: {e}")
        
        # Check for Raspberry Pi specific info
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                if 'BCM' in cpuinfo or 'ARM' in cpuinfo:
                    info["is_raspberry_pi"] = True
                    info["arm_processor"] = True
                else:
                    info["is_raspberry_pi"] = False
                    info["arm_processor"] = False
        except:
            info["is_raspberry_pi"] = False
            info["arm_processor"] = False
        
        return info
    
    def _collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect current performance metrics."""
        metrics = {}
        
        if PSUTIL_AVAILABLE:
            try:
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_freq = psutil.cpu_freq()
                
                # Memory metrics
                memory = psutil.virtual_memory()
                
                # Disk metrics
                disk = psutil.disk_usage('/')
                
                metrics.update({
                    "cpu_percent": cpu_percent,
                    "cpu_freq_current": cpu_freq.current if cpu_freq else 0,
                    "cpu_freq_max": cpu_freq.max if cpu_freq else 0,
                    "memory_percent": memory.percent,
                    "memory_available_mb": memory.available / (1024 * 1024),
                    "memory_used_mb": memory.used / (1024 * 1024),
                    "disk_free_gb": disk.free / (1024 * 1024 * 1024),
                    "disk_used_percent": disk.percent
                })
            except Exception as e:
                logger.error(f"Error collecting performance metrics: {e}")
                metrics["error"] = str(e)
        
        # Temperature if available
        try:
            temp = self.system_monitor.get_temperature()
            if temp > 0:
                metrics["temperature_celsius"] = temp
        except Exception:
            pass
        
        return metrics
    
    def _apply_system_optimizations(self) -> Dict[str, Any]:
        """Apply system-level ARM optimizations."""
        return self.performance_optimizer.optimize_for_raspberry_pi_zero_w()
    
    def _apply_opencv_optimizations(self) -> Dict[str, Any]:
        """Apply OpenCV ARM optimizations."""
        optimizations = []
        
        try:
            if OPENCV_AVAILABLE:
                # Enable OpenCV optimizations
                cv2.setUseOptimized(True)
                optimizations.append("OpenCV optimizations enabled")
                
                # Check optimization status
                if cv2.useOptimized():
                    optimizations.append("OpenCV is using optimized code paths")
                else:
                    optimizations.append("OpenCV optimizations not available")
                
                # Set number of threads for ARM
                cv2.setNumThreads(1)  # Single thread for Pi Zero W
                optimizations.append("OpenCV thread count set to 1 for ARM")
                
                # Configure ARM-specific parameters
                os.environ['OPENCV_OPENCL_DEVICE'] = 'disabled'  # Disable OpenCL on ARM
                optimizations.append("OpenCL disabled for ARM compatibility")
                
            else:
                optimizations.append("OpenCV not available - skipping OpenCV optimizations")
            
            return {
                "success": True,
                "optimizations_applied": optimizations
            }
            
        except Exception as e:
            logger.error(f"Error applying OpenCV optimizations: {e}")
            return {
                "success": False,
                "error": str(e),
                "optimizations_applied": optimizations
            }
    
    def _apply_detection_optimizations(self) -> Dict[str, Any]:
        """Apply detection engine ARM optimizations."""
        try:
            # Apply Raspberry Pi Zero W specific optimizations
            result = self.detection_engine.optimize_for_raspberry_pi_zero_w()
            
            # Additional ARM-specific detection parameters
            self.detection_engine.set_detection_parameters(
                scale_factor=1.2,      # Faster scaling for ARM
                min_neighbors=2,       # Fewer neighbors for speed
                min_size=(50, 50),     # Larger minimum for ARM efficiency
                max_size=(200, 200)    # Smaller maximum for ARM memory
            )
            
            # Set ARM-optimized ROI (focus on counter area)
            self.detection_engine.set_roi((100, 100, 440, 280))  # Center focus area
            
            result["additional_optimizations"] = [
                "Detection parameters optimized for ARM performance",
                "ROI focused on counter area for efficiency"
            ]
            
            return result
            
        except Exception as e:
            logger.error(f"Error applying detection optimizations: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _apply_memory_optimizations(self) -> Dict[str, Any]:
        """Apply memory optimizations for ARM."""
        optimizations = []
        
        try:
            import gc
            
            # Set aggressive garbage collection for ARM
            old_thresholds = gc.get_threshold()
            gc.set_threshold(500, 8, 8)  # More aggressive for ARM
            optimizations.append(f"Garbage collection thresholds changed from {old_thresholds} to (500, 8, 8)")
            
            # Force initial garbage collection
            collected = gc.collect()
            optimizations.append(f"Initial garbage collection freed {collected} objects")
            
            # Set memory-related environment variables
            os.environ['PYTHONHASHSEED'] = '0'  # Consistent hashing for ARM
            optimizations.append("Python hash seed set for ARM consistency")
            
            # Configure swap usage if possible
            try:
                with open('/proc/sys/vm/swappiness', 'r') as f:
                    current_swappiness = f.read().strip()
                
                with open('/proc/sys/vm/swappiness', 'w') as f:
                    f.write('10')  # Reduce swap usage
                optimizations.append(f"Swappiness reduced from {current_swappiness} to 10")
                
            except Exception as e:
                optimizations.append(f"Could not modify swappiness: {e}")
            
            return {
                "success": True,
                "optimizations_applied": optimizations
            }
            
        except Exception as e:
            logger.error(f"Error applying memory optimizations: {e}")
            return {
                "success": False,
                "error": str(e),
                "optimizations_applied": optimizations
            }
    
    def _apply_performance_optimizations(self) -> Dict[str, Any]:
        """Apply performance optimizer ARM settings."""
        try:
            # Start performance monitoring
            self.performance_optimizer.start_monitoring()
            
            # Set ARM-optimized performance levels
            self.performance_optimizer.current_optimization_level = 1  # Start with optimized level
            self.performance_optimizer._apply_optimization_level()
            
            # Apply ARM cache optimizations
            self.performance_optimizer._optimize_arm_cache_usage()
            
            # Configure ARM-specific threading
            os.environ['OMP_NUM_THREADS'] = '1'
            os.environ['OPENBLAS_NUM_THREADS'] = '1'
            os.environ['MKL_NUM_THREADS'] = '1'
            
            return {
                "success": True,
                "optimizations_applied": [
                    "Performance monitoring started",
                    "Optimization level set to 1 (optimized)",
                    "ARM cache usage optimized",
                    "Single-threaded processing enabled for ARM"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error applying performance optimizations: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate ARM-specific optimization recommendations."""
        recommendations = []
        
        # Analyze performance improvement
        before = results.get("performance_before", {})
        after = results.get("performance_after", {})
        
        if before and after:
            cpu_before = before.get("cpu_percent", 0)
            cpu_after = after.get("cpu_percent", 0)
            memory_before = before.get("memory_percent", 0)
            memory_after = after.get("memory_percent", 0)
            
            if cpu_after < cpu_before:
                recommendations.append(f"CPU usage improved: {cpu_before:.1f}% → {cpu_after:.1f}%")
            elif cpu_after > 50:
                recommendations.append("CPU usage still high - consider more aggressive optimizations")
            
            if memory_after < memory_before:
                recommendations.append(f"Memory usage improved: {memory_before:.1f}% → {memory_after:.1f}%")
            elif memory_after > 70:
                recommendations.append("Memory usage still high - consider reducing frame caching")
        
        # System-specific recommendations
        system_info = results.get("system_info", {})
        if system_info.get("is_raspberry_pi"):
            recommendations.extend([
                "Raspberry Pi detected - ensure adequate power supply (2.5A minimum)",
                "Use 'sudo raspi-config' to allocate 128MB+ GPU memory",
                "Consider enabling camera interface if not already enabled",
                "Monitor temperature with 'vcgencmd measure_temp'"
            ])
        
        if system_info.get("arm_processor"):
            recommendations.extend([
                "ARM processor detected - single-threaded optimizations applied",
                "Consider compiling OpenCV with ARM NEON support for better performance",
                "Use high-speed SD card (Class 10+) for better I/O performance"
            ])
        
        # Performance-based recommendations
        if after.get("cpu_percent", 0) > 50:
            recommendations.append("Consider reducing detection frequency or frame resolution")
        
        if after.get("memory_percent", 0) > 80:
            recommendations.append("Consider more aggressive garbage collection or smaller frame buffers")
        
        if after.get("temperature_celsius", 0) > 70:
            recommendations.append("High temperature detected - consider adding cooling or reducing processing load")
        
        # General ARM recommendations
        recommendations.extend([
            "Monitor system performance regularly with the performance test script",
            "Consider overclocking if adequate cooling is available",
            "Use 'htop' to monitor real-time system performance",
            "Regularly update system packages for latest ARM optimizations"
        ])
        
        return recommendations
    
    def save_results(self, filename: str = None) -> str:
        """Save optimization results to file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"arm_optimization_results_{timestamp}.json"
        
        try:
            import json
            
            # Convert datetime objects for JSON serialization
            def serialize_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: serialize_datetime(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [serialize_datetime(item) for item in obj]
                else:
                    return obj
            
            serializable_results = serialize_datetime(self.optimization_results)
            
            with open(filename, 'w') as f:
                json.dump(serializable_results, f, indent=2)
            
            logger.info(f"ARM optimization results saved to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error saving optimization results: {e}")
            return ""
    
    def print_summary(self) -> None:
        """Print optimization summary."""
        print("\n" + "="*60)
        print("ARM OPTIMIZATION SUMMARY")
        print("="*60)
        
        if not self.optimization_results:
            print("No optimization results available")
            return
        
        # System info
        system_info = self.optimization_results.get("system_info", {})
        print(f"System: {'Raspberry Pi' if system_info.get('is_raspberry_pi') else 'Generic'}")
        print(f"ARM Processor: {'Yes' if system_info.get('arm_processor') else 'No'}")
        print(f"CPU Count: {system_info.get('cpu_count', 'Unknown')}")
        print(f"Memory: {system_info.get('memory_total_mb', 0):.0f} MB")
        
        # Performance comparison
        before = self.optimization_results.get("performance_before", {})
        after = self.optimization_results.get("performance_after", {})
        
        if before and after:
            print("\nPerformance Comparison:")
            print(f"CPU Usage: {before.get('cpu_percent', 0):.1f}% → {after.get('cpu_percent', 0):.1f}%")
            print(f"Memory Usage: {before.get('memory_percent', 0):.1f}% → {after.get('memory_percent', 0):.1f}%")
            
            temp_before = before.get('temperature_celsius')
            temp_after = after.get('temperature_celsius')
            if temp_before and temp_after:
                print(f"Temperature: {temp_before:.1f}°C → {temp_after:.1f}°C")
        
        # Optimizations applied
        optimizations = self.optimization_results.get("optimizations", {})
        total_optimizations = 0
        
        print("\nOptimizations Applied:")
        for category, result in optimizations.items():
            if result.get("success"):
                applied = result.get("optimizations_applied", [])
                print(f"  {category.title()}: {len(applied)} optimizations")
                total_optimizations += len(applied)
            else:
                print(f"  {category.title()}: Failed - {result.get('error', 'Unknown error')}")
        
        print(f"\nTotal Optimizations Applied: {total_optimizations}")
        
        # Top recommendations
        recommendations = self.optimization_results.get("recommendations", [])
        if recommendations:
            print("\nTop Recommendations:")
            for i, rec in enumerate(recommendations[:5], 1):
                print(f"  {i}. {rec}")
        
        print("\n" + "="*60)


def main():
    """Main function to run ARM optimizations."""
    print("Starting ARM Optimization for Raspberry Pi Zero W...")
    
    optimizer = ARMOptimizer()
    
    try:
        # Apply all optimizations
        results = optimizer.apply_all_optimizations()
        
        # Print summary
        optimizer.print_summary()
        
        # Save results
        filename = optimizer.save_results()
        if filename:
            print(f"\nDetailed results saved to: {filename}")
        
        # Check if optimizations were successful
        optimizations = results.get("optimizations", {})
        success_count = sum(1 for result in optimizations.values() if result.get("success"))
        total_count = len(optimizations)
        
        if success_count == total_count:
            print("\n✅ ARM optimization completed successfully!")
            return 0
        elif success_count > 0:
            print(f"\n⚠️  ARM optimization partially successful ({success_count}/{total_count})")
            return 1
        else:
            print("\n❌ ARM optimization failed")
            return 2
    
    except Exception as e:
        logger.error(f"ARM optimization failed: {e}")
        print(f"\n❌ ARM optimization failed: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())