"""Performance profiler for identifying bottlenecks in the detection pipeline."""

import logging
import time
import cProfile
import pstats
import io
from typing import Dict, Any, List, Optional, Callable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ProfileResult:
    """Profile result data structure."""
    function_name: str
    total_time: float
    cumulative_time: float
    call_count: int
    time_per_call: float
    percentage_of_total: float


@dataclass
class BottleneckAnalysis:
    """Bottleneck analysis result."""
    timestamp: datetime
    total_execution_time: float
    top_bottlenecks: List[ProfileResult]
    recommendations: List[str]
    profile_data: str


class PerformanceProfiler:
    """Performance profiler for the cat detection system."""
    
    def __init__(self):
        self.profiler = None
        self.profiling_active = False
        self.profile_results: List[BottleneckAnalysis] = []
        
        # Timing contexts
        self._timing_contexts: Dict[str, List[float]] = {}
        
        logger.info("Performance profiler initialized")
    
    def start_profiling(self) -> None:
        """Start performance profiling."""
        if self.profiling_active:
            logger.warning("Profiling already active")
            return
        
        self.profiler = cProfile.Profile()
        self.profiler.enable()
        self.profiling_active = True
        logger.info("Performance profiling started")
    
    def stop_profiling(self) -> BottleneckAnalysis:
        """Stop profiling and analyze results."""
        if not self.profiling_active or not self.profiler:
            logger.warning("No active profiling session")
            return None
        
        self.profiler.disable()
        self.profiling_active = False
        
        # Analyze profile results
        analysis = self._analyze_profile_results()
        self.profile_results.append(analysis)
        
        logger.info(f"Profiling stopped - found {len(analysis.top_bottlenecks)} bottlenecks")
        return analysis
    
    def _analyze_profile_results(self) -> BottleneckAnalysis:
        """Analyze profiling results and identify bottlenecks."""
        # Capture profile stats
        stats_stream = io.StringIO()
        stats = pstats.Stats(self.profiler, stream=stats_stream)
        stats.sort_stats('cumulative')
        stats.print_stats(20)  # Top 20 functions
        
        profile_data = stats_stream.getvalue()
        
        # Parse stats for bottleneck analysis
        bottlenecks = self._extract_bottlenecks(stats)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(bottlenecks)
        
        return BottleneckAnalysis(
            timestamp=datetime.now(),
            total_execution_time=sum(bottleneck.total_time for bottleneck in bottlenecks[:5]),
            top_bottlenecks=bottlenecks,
            recommendations=recommendations,
            profile_data=profile_data
        )
    
    def _extract_bottlenecks(self, stats: pstats.Stats) -> List[ProfileResult]:
        """Extract bottleneck information from profile stats."""
        bottlenecks = []
        
        try:
            # Get stats data
            total_time = 0
            for func, (cc, nc, tt, ct, callers) in stats.stats.items():
                total_time += tt
            
            # Extract top functions by cumulative time
            sorted_stats = sorted(stats.stats.items(), key=lambda x: x[1][3], reverse=True)
            
            for i, (func, (cc, nc, tt, ct, callers)) in enumerate(sorted_stats[:15]):
                func_name = f"{func[0]}:{func[1]}({func[2]})"
                
                # Skip built-in functions and profiler overhead
                if any(skip in func_name.lower() for skip in ['<built-in>', 'profiler', '__']):
                    continue
                
                percentage = (ct / total_time * 100) if total_time > 0 else 0
                time_per_call = ct / cc if cc > 0 else 0
                
                bottleneck = ProfileResult(
                    function_name=func_name,
                    total_time=tt,
                    cumulative_time=ct,
                    call_count=cc,
                    time_per_call=time_per_call,
                    percentage_of_total=percentage
                )
                
                bottlenecks.append(bottleneck)
                
                if len(bottlenecks) >= 10:  # Limit to top 10
                    break
        
        except Exception as e:
            logger.error(f"Error extracting bottlenecks: {e}")
        
        return bottlenecks
    
    def _generate_recommendations(self, bottlenecks: List[ProfileResult]) -> List[str]:
        """Generate optimization recommendations based on bottlenecks."""
        recommendations = []
        
        for bottleneck in bottlenecks[:5]:  # Top 5 bottlenecks
            func_name = bottleneck.function_name.lower()
            
            # OpenCV/Computer Vision optimizations
            if any(cv_func in func_name for cv_func in ['cv2', 'detectmultiscale', 'cascade']):
                recommendations.append(
                    f"OpenCV bottleneck detected in {bottleneck.function_name} "
                    f"({bottleneck.percentage_of_total:.1f}% of time). "
                    "Consider: reducing image resolution, adjusting detection parameters, "
                    "or using ROI to limit detection area."
                )
            
            # Image processing optimizations
            elif any(img_func in func_name for img_func in ['resize', 'convert', 'preprocess']):
                recommendations.append(
                    f"Image processing bottleneck in {bottleneck.function_name} "
                    f"({bottleneck.percentage_of_total:.1f}% of time). "
                    "Consider: caching processed frames, reducing image quality, "
                    "or optimizing preprocessing pipeline."
                )
            
            # I/O bottlenecks
            elif any(io_func in func_name for io_func in ['read', 'write', 'save', 'load']):
                recommendations.append(
                    f"I/O bottleneck detected in {bottleneck.function_name} "
                    f"({bottleneck.percentage_of_total:.1f}% of time). "
                    "Consider: asynchronous I/O, reducing file sizes, "
                    "or batching operations."
                )
            
            # Memory/GC bottlenecks
            elif any(mem_func in func_name for mem_func in ['gc', 'collect', 'alloc']):
                recommendations.append(
                    f"Memory management bottleneck in {bottleneck.function_name} "
                    f"({bottleneck.percentage_of_total:.1f}% of time). "
                    "Consider: reducing object creation, implementing object pooling, "
                    "or optimizing data structures."
                )
            
            # Network bottlenecks
            elif any(net_func in func_name for net_func in ['send', 'request', 'http', 'smtp']):
                recommendations.append(
                    f"Network bottleneck detected in {bottleneck.function_name} "
                    f"({bottleneck.percentage_of_total:.1f}% of time). "
                    "Consider: asynchronous networking, connection pooling, "
                    "or reducing payload sizes."
                )
            
            # General high-impact functions
            elif bottleneck.percentage_of_total > 10:
                recommendations.append(
                    f"High-impact function {bottleneck.function_name} consuming "
                    f"{bottleneck.percentage_of_total:.1f}% of execution time. "
                    "Consider optimizing this function or reducing call frequency."
                )
        
        if not recommendations:
            recommendations.append("No significant bottlenecks detected in profiling data.")
        
        return recommendations
    
    @contextmanager
    def profile_context(self, context_name: str):
        """Context manager for profiling specific code blocks."""
        start_time = time.time()
        
        if self.profiling_active and self.profiler:
            self.profiler.enable()
        
        try:
            yield
        finally:
            if self.profiling_active and self.profiler:
                self.profiler.disable()
            
            execution_time = time.time() - start_time
            
            # Store timing data
            if context_name not in self._timing_contexts:
                self._timing_contexts[context_name] = []
            
            self._timing_contexts[context_name].append(execution_time)
            
            # Keep only recent timings (last 100)
            if len(self._timing_contexts[context_name]) > 100:
                self._timing_contexts[context_name].pop(0)
    
    def time_function(self, func: Callable, *args, **kwargs) -> tuple:
        """Time a function execution and return result with timing."""
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            return result, execution_time
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error timing function {func.__name__}: {e}")
            raise
    
    def get_timing_stats(self, context_name: str) -> Dict[str, float]:
        """Get timing statistics for a specific context."""
        if context_name not in self._timing_contexts:
            return {"error": "No timing data available"}
        
        timings = self._timing_contexts[context_name]
        
        if not timings:
            return {"error": "No timing data available"}
        
        return {
            "count": len(timings),
            "total_time": sum(timings),
            "average_time": sum(timings) / len(timings),
            "min_time": min(timings),
            "max_time": max(timings),
            "recent_average": sum(timings[-10:]) / min(10, len(timings))
        }
    
    def get_all_timing_stats(self) -> Dict[str, Dict[str, float]]:
        """Get timing statistics for all contexts."""
        return {
            context: self.get_timing_stats(context)
            for context in self._timing_contexts.keys()
        }
    
    def profile_detection_pipeline(self, pipeline_func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """Profile the entire detection pipeline."""
        logger.info("Starting detection pipeline profiling...")
        
        # Start profiling
        self.start_profiling()
        
        try:
            # Run the pipeline function
            start_time = time.time()
            result = pipeline_func(*args, **kwargs)
            total_time = time.time() - start_time
            
            # Stop profiling and analyze
            analysis = self.stop_profiling()
            
            return {
                "success": True,
                "total_execution_time": total_time,
                "analysis": analysis,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error during pipeline profiling: {e}")
            if self.profiling_active:
                self.stop_profiling()
            
            return {
                "success": False,
                "error": str(e),
                "total_execution_time": 0,
                "analysis": None,
                "result": None
            }
    
    def benchmark_frame_processing(self, frame_processor: Callable, 
                                 test_frames: List[Any], 
                                 iterations: int = 10) -> Dict[str, Any]:
        """Benchmark frame processing performance."""
        logger.info(f"Starting frame processing benchmark with {len(test_frames)} frames, {iterations} iterations")
        
        results = {
            "total_frames_processed": 0,
            "total_time": 0,
            "average_fps": 0,
            "min_processing_time": float('inf'),
            "max_processing_time": 0,
            "processing_times": []
        }
        
        try:
            for iteration in range(iterations):
                for frame in test_frames:
                    start_time = time.time()
                    
                    # Process frame
                    frame_processor(frame)
                    
                    processing_time = time.time() - start_time
                    
                    # Update results
                    results["total_frames_processed"] += 1
                    results["total_time"] += processing_time
                    results["processing_times"].append(processing_time)
                    results["min_processing_time"] = min(results["min_processing_time"], processing_time)
                    results["max_processing_time"] = max(results["max_processing_time"], processing_time)
            
            # Calculate averages
            if results["total_time"] > 0:
                results["average_fps"] = results["total_frames_processed"] / results["total_time"]
            
            results["average_processing_time"] = (
                sum(results["processing_times"]) / len(results["processing_times"])
                if results["processing_times"] else 0
            )
            
            logger.info(f"Benchmark completed: {results['average_fps']:.2f} FPS average")
            
        except Exception as e:
            logger.error(f"Error during frame processing benchmark: {e}")
            results["error"] = str(e)
        
        return results
    
    def get_latest_analysis(self) -> Optional[BottleneckAnalysis]:
        """Get the most recent bottleneck analysis."""
        return self.profile_results[-1] if self.profile_results else None
    
    def get_profiling_summary(self) -> Dict[str, Any]:
        """Get a summary of all profiling data."""
        return {
            "total_profiles": len(self.profile_results),
            "timing_contexts": list(self._timing_contexts.keys()),
            "latest_analysis": self.get_latest_analysis(),
            "timing_stats": self.get_all_timing_stats(),
            "profiling_active": self.profiling_active
        }
    
    def clear_profiling_data(self) -> None:
        """Clear all profiling data."""
        self.profile_results.clear()
        self._timing_contexts.clear()
        logger.info("Profiling data cleared")