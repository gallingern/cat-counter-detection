#!/usr/bin/env python3
"""Performance testing script for Raspberry Pi Zero W optimization."""

import logging
import time
import threading
import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cat_counter_detection.services.performance_profiler import PerformanceProfiler
from cat_counter_detection.services.performance_optimizer import PerformanceOptimizer
from cat_counter_detection.services.system_monitor import SystemMonitor
from cat_counter_detection.detection_pipeline import DetectionPipeline
from cat_counter_detection.config_manager import ConfigManager

# Handle optional imports
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    cv2 = None
    np = None

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerformanceTester:
    """Comprehensive performance testing for Raspberry Pi Zero W."""
    
    def __init__(self):
        self.profiler = PerformanceProfiler()
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()
        self.optimizer = PerformanceOptimizer(self.config)
        self.system_monitor = SystemMonitor()
        
        # Test results
        self.test_results: Dict[str, Any] = {}
        self.baseline_metrics: Optional[Dict[str, float]] = None
        
        # Test frames for benchmarking
        self.test_frames = []
        self._generate_test_frames()
    
    def _generate_test_frames(self) -> None:
        """Generate test frames for benchmarking."""
        if not OPENCV_AVAILABLE:
            logger.warning("OpenCV not available - using mock frames")
            # Create mock frames
            for i in range(10):
                self.test_frames.append([[0 for _ in range(640)] for _ in range(480)])
            return
        
        # Generate realistic test frames
        for i in range(10):
            # Create a frame with some noise and patterns
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            
            # Add some rectangular shapes to simulate objects
            cv2.rectangle(frame, (100 + i*10, 100 + i*5), (200 + i*10, 200 + i*5), (255, 255, 255), -1)
            cv2.rectangle(frame, (300 + i*5, 200 + i*10), (400 + i*5, 300 + i*10), (128, 128, 128), -1)
            
            self.test_frames.append(frame)
        
        logger.info(f"Generated {len(self.test_frames)} test frames")
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive performance test suite."""
        logger.info("Starting comprehensive performance test...")
        
        # Initialize test results
        self.test_results = {
            "test_start_time": datetime.now().isoformat(),
            "system_info": self._get_system_info(),
            "baseline_performance": {},
            "optimization_levels": {},
            "bottleneck_analysis": {},
            "recommendations": [],
            "test_summary": {}
        }
        
        try:
            # Step 1: Collect baseline performance metrics
            logger.info("Step 1: Collecting baseline performance metrics...")
            self.baseline_metrics = self._collect_baseline_metrics()
            self.test_results["baseline_performance"] = self.baseline_metrics
            
            # Step 2: Test different optimization levels
            logger.info("Step 2: Testing optimization levels...")
            self._test_optimization_levels()
            
            # Step 3: Profile detection pipeline for bottlenecks
            logger.info("Step 3: Profiling detection pipeline...")
            self._profile_detection_pipeline()
            
            # Step 4: Test frame processing optimizations
            logger.info("Step 4: Testing frame processing optimizations...")
            self._test_frame_processing_optimizations()
            
            # Step 5: Test memory optimization
            logger.info("Step 5: Testing memory optimization...")
            self._test_memory_optimization()
            
            # Step 6: Generate recommendations
            logger.info("Step 6: Generating optimization recommendations...")
            self._generate_optimization_recommendations()
            
            # Step 7: Create test summary
            self._create_test_summary()
            
            logger.info("Comprehensive performance test completed successfully")
            
        except Exception as e:
            logger.error(f"Error during performance testing: {e}")
            self.test_results["error"] = str(e)
        
        return self.test_results
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        info = {
            "timestamp": datetime.now().isoformat(),
            "opencv_available": OPENCV_AVAILABLE,
            "psutil_available": PSUTIL_AVAILABLE
        }
        
        if PSUTIL_AVAILABLE:
            try:
                info.update({
                    "cpu_count": psutil.cpu_count(),
                    "memory_total_mb": psutil.virtual_memory().total / (1024 * 1024),
                    "disk_total_gb": psutil.disk_usage('/').total / (1024 * 1024 * 1024),
                    "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
                })
            except Exception as e:
                logger.warning(f"Error getting system info: {e}")
        
        return info
    
    def _collect_baseline_metrics(self) -> Dict[str, float]:
        """Collect baseline performance metrics."""
        metrics = {}
        
        if PSUTIL_AVAILABLE:
            # CPU usage over 5 seconds
            cpu_samples = []
            for _ in range(5):
                cpu_samples.append(psutil.cpu_percent(interval=1))
            
            metrics["baseline_cpu_percent"] = sum(cpu_samples) / len(cpu_samples)
            metrics["baseline_memory_percent"] = psutil.virtual_memory().percent
            metrics["baseline_memory_available_mb"] = psutil.virtual_memory().available / (1024 * 1024)
        
        # Temperature if available
        try:
            temp = self.system_monitor.get_temperature()
            if temp > 0:
                metrics["baseline_temperature_celsius"] = temp
        except Exception:
            pass
        
        return metrics
    
    def _test_optimization_levels(self) -> None:
        """Test different optimization levels."""
        optimization_results = {}
        
        for level in [0, 1, 2]:  # Normal, Optimized, Aggressive
            logger.info(f"Testing optimization level {level}...")
            
            # Set optimization level
            self.optimizer.current_optimization_level = level
            self.optimizer._apply_optimization_level()
            
            # Run performance test for this level
            level_results = self._run_optimization_level_test(level)
            optimization_results[f"level_{level}"] = level_results
            
            # Brief pause between tests
            time.sleep(2)
        
        self.test_results["optimization_levels"] = optimization_results
    
    def _run_optimization_level_test(self, level: int) -> Dict[str, Any]:
        """Run performance test for a specific optimization level."""
        results = {
            "level": level,
            "settings": self.optimizer.optimization_levels[level].__dict__,
            "performance_metrics": {},
            "frame_processing_results": {}
        }
        
        # Start monitoring
        self.optimizer.start_monitoring()
        
        try:
            # Run frame processing benchmark
            if self.test_frames:
                benchmark_results = self._benchmark_frame_processing_at_level(level)
                results["frame_processing_results"] = benchmark_results
            
            # Collect performance metrics after 10 seconds
            time.sleep(10)
            current_metrics = self.optimizer.get_current_metrics()
            if current_metrics:
                results["performance_metrics"] = {
                    "cpu_percent": current_metrics.cpu_percent,
                    "memory_percent": current_metrics.memory_percent,
                    "memory_available_mb": current_metrics.memory_available_mb,
                    "temperature_celsius": current_metrics.temperature_celsius,
                    "fps": current_metrics.fps
                }
        
        finally:
            self.optimizer.stop_monitoring()
        
        return results
    
    def _benchmark_frame_processing_at_level(self, level: int) -> Dict[str, Any]:
        """Benchmark frame processing at specific optimization level."""
        if not self.test_frames:
            return {"error": "No test frames available"}
        
        # Create a simple frame processor
        def process_frame(frame):
            # Simulate frame processing with optimization
            optimized_frame = self.optimizer.optimize_frame_processing(frame, 0)
            if optimized_frame is not None and OPENCV_AVAILABLE:
                # Simulate some processing
                if isinstance(optimized_frame, np.ndarray):
                    cv2.GaussianBlur(optimized_frame, (5, 5), 0)
            return optimized_frame
        
        # Run benchmark
        return self.profiler.benchmark_frame_processing(
            process_frame, 
            self.test_frames, 
            iterations=3
        )
    
    def _profile_detection_pipeline(self) -> None:
        """Profile the detection pipeline to identify bottlenecks."""
        try:
            # Create a minimal pipeline for profiling
            pipeline = DetectionPipeline(self.config_manager)
            
            # Profile pipeline initialization
            def init_pipeline():
                pipeline._load_detection_model()
                return True
            
            init_profile = self.profiler.profile_detection_pipeline(init_pipeline)
            
            # Profile frame processing if we have test frames
            if self.test_frames and OPENCV_AVAILABLE:
                def process_test_frames():
                    for frame in self.test_frames[:3]:  # Process first 3 frames
                        pipeline._process_frame(frame)
                    return True
                
                processing_profile = self.profiler.profile_detection_pipeline(process_test_frames)
                
                self.test_results["bottleneck_analysis"] = {
                    "initialization": init_profile,
                    "frame_processing": processing_profile
                }
            else:
                self.test_results["bottleneck_analysis"] = {
                    "initialization": init_profile,
                    "frame_processing": {"error": "No test frames or OpenCV not available"}
                }
        
        except Exception as e:
            logger.error(f"Error profiling detection pipeline: {e}")
            self.test_results["bottleneck_analysis"] = {"error": str(e)}
    
    def _test_frame_processing_optimizations(self) -> None:
        """Test various frame processing optimizations."""
        if not OPENCV_AVAILABLE or not self.test_frames:
            self.test_results["frame_processing_optimizations"] = {
                "error": "OpenCV not available or no test frames"
            }
            return
        
        optimizations = {}
        
        # Test 1: Frame downsampling
        logger.info("Testing frame downsampling...")
        optimizations["downsampling"] = self._test_frame_downsampling()
        
        # Test 2: ROI processing
        logger.info("Testing ROI processing...")
        optimizations["roi_processing"] = self._test_roi_processing()
        
        # Test 3: Frame skipping
        logger.info("Testing frame skipping...")
        optimizations["frame_skipping"] = self._test_frame_skipping()
        
        self.test_results["frame_processing_optimizations"] = optimizations
    
    def _test_frame_downsampling(self) -> Dict[str, Any]:
        """Test frame downsampling performance impact."""
        if not OPENCV_AVAILABLE:
            return {"error": "OpenCV not available"}
        
        results = {}
        downsample_factors = [1.0, 0.8, 0.6, 0.4]
        
        for factor in downsample_factors:
            logger.info(f"Testing downsample factor {factor}...")
            
            def process_with_downsample(frame):
                if factor < 1.0:
                    height, width = frame.shape[:2]
                    new_height = int(height * factor)
                    new_width = int(width * factor)
                    return cv2.resize(frame, (new_width, new_height))
                return frame
            
            benchmark = self.profiler.benchmark_frame_processing(
                process_with_downsample,
                self.test_frames,
                iterations=2
            )
            
            results[f"factor_{factor}"] = benchmark
        
        return results
    
    def _test_roi_processing(self) -> Dict[str, Any]:
        """Test ROI processing performance impact."""
        if not OPENCV_AVAILABLE:
            return {"error": "OpenCV not available"}
        
        results = {}
        roi_sizes = [
            (0, 0, 640, 480),  # Full frame
            (160, 120, 320, 240),  # Half frame
            (200, 150, 240, 180),  # Quarter frame
        ]
        
        for i, roi in enumerate(roi_sizes):
            logger.info(f"Testing ROI size {roi}...")
            
            def process_with_roi(frame):
                x, y, w, h = roi
                return frame[y:y+h, x:x+w]
            
            benchmark = self.profiler.benchmark_frame_processing(
                process_with_roi,
                self.test_frames,
                iterations=2
            )
            
            results[f"roi_{i}"] = {
                "roi": roi,
                "benchmark": benchmark
            }
        
        return results
    
    def _test_frame_skipping(self) -> Dict[str, Any]:
        """Test frame skipping performance impact."""
        results = {}
        skip_patterns = [0, 1, 2, 3]  # Skip every N frames
        
        for skip_count in skip_patterns:
            logger.info(f"Testing frame skip pattern: {skip_count}...")
            
            processed_frames = 0
            skipped_frames = 0
            
            def process_with_skipping(frame):
                nonlocal processed_frames, skipped_frames
                if skip_count == 0 or (processed_frames + skipped_frames) % (skip_count + 1) == 0:
                    processed_frames += 1
                    return frame
                else:
                    skipped_frames += 1
                    return None
            
            start_time = time.time()
            for frame in self.test_frames * 3:  # Process frames 3 times
                process_with_skipping(frame)
            total_time = time.time() - start_time
            
            effective_fps = processed_frames / total_time if total_time > 0 else 0
            
            results[f"skip_{skip_count}"] = {
                "skip_count": skip_count,
                "processed_frames": processed_frames,
                "skipped_frames": skipped_frames,
                "total_time": total_time,
                "effective_fps": effective_fps
            }
        
        return results
    
    def _test_memory_optimization(self) -> None:
        """Test memory optimization techniques."""
        if not PSUTIL_AVAILABLE:
            self.test_results["memory_optimization"] = {
                "error": "psutil not available"
            }
            return
        
        memory_tests = {}
        
        # Test 1: Garbage collection impact
        logger.info("Testing garbage collection impact...")
        memory_tests["garbage_collection"] = self._test_garbage_collection()
        
        # Test 2: Object pooling simulation
        logger.info("Testing object creation patterns...")
        memory_tests["object_creation"] = self._test_object_creation_patterns()
        
        self.test_results["memory_optimization"] = memory_tests
    
    def _test_garbage_collection(self) -> Dict[str, Any]:
        """Test garbage collection performance impact."""
        import gc
        
        # Measure memory before
        before_memory = psutil.virtual_memory()
        
        # Create some objects to trigger GC
        large_objects = []
        for i in range(1000):
            large_objects.append([0] * 1000)
        
        # Measure memory after object creation
        after_creation = psutil.virtual_memory()
        
        # Force garbage collection
        start_time = time.time()
        collected = gc.collect()
        gc_time = time.time() - start_time
        
        # Measure memory after GC
        after_gc = psutil.virtual_memory()
        
        # Clean up
        large_objects.clear()
        
        return {
            "memory_before_mb": before_memory.used / (1024 * 1024),
            "memory_after_creation_mb": after_creation.used / (1024 * 1024),
            "memory_after_gc_mb": after_gc.used / (1024 * 1024),
            "objects_collected": collected,
            "gc_time_seconds": gc_time,
            "memory_freed_mb": (after_creation.used - after_gc.used) / (1024 * 1024)
        }
    
    def _test_object_creation_patterns(self) -> Dict[str, Any]:
        """Test different object creation patterns."""
        results = {}
        
        # Test 1: List comprehension vs loop
        start_time = time.time()
        list_comp = [i * 2 for i in range(10000)]
        list_comp_time = time.time() - start_time
        
        start_time = time.time()
        loop_list = []
        for i in range(10000):
            loop_list.append(i * 2)
        loop_time = time.time() - start_time
        
        results["list_creation"] = {
            "list_comprehension_time": list_comp_time,
            "loop_time": loop_time,
            "comprehension_faster": list_comp_time < loop_time
        }
        
        # Test 2: String concatenation patterns
        start_time = time.time()
        join_result = ''.join([str(i) for i in range(1000)])
        join_time = time.time() - start_time
        
        start_time = time.time()
        concat_result = ''
        for i in range(1000):
            concat_result += str(i)
        concat_time = time.time() - start_time
        
        results["string_creation"] = {
            "join_time": join_time,
            "concatenation_time": concat_time,
            "join_faster": join_time < concat_time
        }
        
        return results
    
    def _generate_optimization_recommendations(self) -> None:
        """Generate optimization recommendations based on test results."""
        recommendations = []
        
        # Analyze baseline performance
        if self.baseline_metrics:
            if self.baseline_metrics.get("baseline_cpu_percent", 0) > 50:
                recommendations.append(
                    "High baseline CPU usage detected. Consider reducing background processes "
                    "or using more aggressive optimization levels."
                )
            
            if self.baseline_metrics.get("baseline_memory_percent", 0) > 70:
                recommendations.append(
                    "High baseline memory usage detected. Consider enabling more frequent "
                    "garbage collection or reducing frame caching."
                )
            
            temp = self.baseline_metrics.get("baseline_temperature_celsius")
            if temp and temp > 60:
                recommendations.append(
                    f"High baseline temperature ({temp:.1f}°C) detected. Consider adding "
                    "cooling or reducing processing intensity."
                )
        
        # Analyze optimization level results
        opt_levels = self.test_results.get("optimization_levels", {})
        if opt_levels:
            best_fps = 0
            best_level = 0
            
            for level_key, level_data in opt_levels.items():
                fps = level_data.get("frame_processing_results", {}).get("average_fps", 0)
                if fps > best_fps:
                    best_fps = fps
                    best_level = int(level_key.split("_")[1])
            
            if best_fps < 1.0:
                recommendations.append(
                    f"Best achieved FPS is {best_fps:.2f}, below target of 1.0 FPS. "
                    f"Consider using optimization level {best_level} or higher, "
                    "reducing frame resolution, or increasing frame skip intervals."
                )
            else:
                recommendations.append(
                    f"Target FPS achieved with optimization level {best_level}. "
                    f"Best performance: {best_fps:.2f} FPS."
                )
        
        # Analyze frame processing optimizations
        frame_opts = self.test_results.get("frame_processing_optimizations", {})
        if "downsampling" in frame_opts:
            downsample_results = frame_opts["downsampling"]
            best_factor = None
            best_fps = 0
            
            for factor_key, result in downsample_results.items():
                if isinstance(result, dict) and "average_fps" in result:
                    fps = result["average_fps"]
                    if fps > best_fps:
                        best_fps = fps
                        best_factor = factor_key
            
            if best_factor and best_factor != "factor_1.0":
                factor_value = best_factor.split("_")[1]
                recommendations.append(
                    f"Frame downsampling to {factor_value} factor provides best performance "
                    f"({best_fps:.2f} FPS). Consider implementing this optimization."
                )
        
        # Analyze bottlenecks
        bottlenecks = self.test_results.get("bottleneck_analysis", {})
        if "frame_processing" in bottlenecks:
            processing_analysis = bottlenecks["frame_processing"]
            if processing_analysis.get("success") and processing_analysis.get("analysis"):
                analysis = processing_analysis["analysis"]
                if analysis.recommendations:
                    recommendations.extend(analysis.recommendations[:3])  # Top 3 recommendations
        
        # Add general Raspberry Pi Zero W recommendations
        recommendations.extend([
            "For Raspberry Pi Zero W: Ensure adequate power supply (2.5A minimum) to prevent throttling.",
            "Consider using a high-speed SD card (Class 10 or better) for better I/O performance.",
            "Monitor CPU temperature and add passive cooling if temperature exceeds 70°C regularly.",
            "Use 'sudo raspi-config' to enable camera interface and allocate sufficient GPU memory (128MB+)."
        ])
        
        self.test_results["recommendations"] = recommendations
    
    def _create_test_summary(self) -> None:
        """Create a summary of test results."""
        summary = {
            "test_duration_seconds": 0,
            "total_tests_run": 0,
            "performance_target_met": False,
            "recommended_optimization_level": 0,
            "key_findings": []
        }
        
        # Calculate test duration
        start_time_str = self.test_results.get("test_start_time")
        if start_time_str:
            start_time = datetime.fromisoformat(start_time_str)
            summary["test_duration_seconds"] = (datetime.now() - start_time).total_seconds()
        
        # Count tests run
        test_sections = ["optimization_levels", "frame_processing_optimizations", "memory_optimization"]
        summary["total_tests_run"] = sum(1 for section in test_sections if section in self.test_results)
        
        # Determine if performance target was met
        opt_levels = self.test_results.get("optimization_levels", {})
        best_fps = 0
        best_level = 0
        
        for level_key, level_data in opt_levels.items():
            fps = level_data.get("frame_processing_results", {}).get("average_fps", 0)
            if fps > best_fps:
                best_fps = fps
                best_level = int(level_key.split("_")[1])
        
        summary["performance_target_met"] = best_fps >= 1.0
        summary["recommended_optimization_level"] = best_level
        summary["best_achieved_fps"] = best_fps
        
        # Key findings
        if best_fps >= 1.0:
            summary["key_findings"].append(f"Performance target met: {best_fps:.2f} FPS achieved")
        else:
            summary["key_findings"].append(f"Performance target not met: {best_fps:.2f} FPS (target: 1.0 FPS)")
        
        if self.baseline_metrics:
            cpu = self.baseline_metrics.get("baseline_cpu_percent", 0)
            memory = self.baseline_metrics.get("baseline_memory_percent", 0)
            summary["key_findings"].append(f"Baseline system load: {cpu:.1f}% CPU, {memory:.1f}% memory")
        
        self.test_results["test_summary"] = summary
    
    def save_results(self, filename: str = None) -> str:
        """Save test results to file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_test_results_{timestamp}.json"
        
        try:
            import json
            
            # Convert complex objects to serializable format
            def serialize_object(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif hasattr(obj, '__dict__'):
                    return {
                        'type': obj.__class__.__name__,
                        'data': {k: serialize_object(v) for k, v in obj.__dict__.items()}
                    }
                elif isinstance(obj, (list, tuple)):
                    return [serialize_object(item) for item in obj]
                elif isinstance(obj, dict):
                    return {k: serialize_object(v) for k, v in obj.items()}
                else:
                    return obj
            
            serializable_results = serialize_object(self.test_results)
            
            with open(filename, 'w') as f:
                json.dump(serializable_results, f, indent=2)
            
            logger.info(f"Test results saved to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error saving test results: {e}")
            return ""
    
    def print_summary(self) -> None:
        """Print a summary of test results."""
        print("\n" + "="*60)
        print("PERFORMANCE TEST SUMMARY")
        print("="*60)
        
        summary = self.test_results.get("test_summary", {})
        
        print(f"Test Duration: {summary.get('test_duration_seconds', 0):.1f} seconds")
        print(f"Tests Run: {summary.get('total_tests_run', 0)}")
        print(f"Performance Target Met: {'YES' if summary.get('performance_target_met') else 'NO'}")
        print(f"Best Achieved FPS: {summary.get('best_achieved_fps', 0):.2f}")
        print(f"Recommended Optimization Level: {summary.get('recommended_optimization_level', 0)}")
        
        print("\nKey Findings:")
        for finding in summary.get("key_findings", []):
            print(f"  • {finding}")
        
        print("\nTop Recommendations:")
        for i, rec in enumerate(self.test_results.get("recommendations", [])[:5], 1):
            print(f"  {i}. {rec}")
        
        print("\n" + "="*60)


def main():
    """Main function to run performance tests."""
    print("Starting Raspberry Pi Zero W Performance Optimization Tests...")
    
    tester = PerformanceTester()
    
    try:
        # Run comprehensive test
        results = tester.run_comprehensive_test()
        
        # Print summary
        tester.print_summary()
        
        # Save results
        filename = tester.save_results()
        if filename:
            print(f"\nDetailed results saved to: {filename}")
        
        # Return success code based on performance target
        summary = results.get("test_summary", {})
        if summary.get("performance_target_met"):
            print("\n✅ Performance optimization successful!")
            return 0
        else:
            print("\n⚠️  Performance target not met - review recommendations")
            return 1
    
    except Exception as e:
        logger.error(f"Performance test failed: {e}")
        print(f"\n❌ Performance test failed: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())