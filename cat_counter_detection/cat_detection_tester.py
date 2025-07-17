"""Cat detection testing and fine-tuning utility for lynx point and tabby cats."""

import logging
import os
import json
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from pathlib import Path

# Handle imports gracefully
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    cv2 = None
    np = None

from .services.enhanced_detection_engine import EnhancedCatDetectionEngine
from .services.model_manager import ModelManager
from .models.detection import Detection

logger = logging.getLogger(__name__)


class CatDetectionTester:
    """Test and fine-tune cat detection for specific cat types and environments."""
    
    def __init__(self, models_dir: str = "models", test_images_dir: str = "test_images"):
        self.models_dir = Path(models_dir)
        self.test_images_dir = Path(test_images_dir)
        self.test_images_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.model_manager = ModelManager(str(self.models_dir))
        self.detection_engine = EnhancedCatDetectionEngine()
        
        # Test configuration
        self.test_results = []
        self.cat_types = ["lynx_point", "tabby", "mixed"]
        self.environments = ["black_counter", "wood_floor", "mixed_lighting"]
        
        # Detection parameters for fine-tuning
        self.confidence_thresholds = [0.5, 0.6, 0.7, 0.8, 0.9]
        self.nms_thresholds = [0.3, 0.4, 0.5, 0.6]
        
        logger.info("Cat detection tester initialized")
    
    def setup_test_environment(self) -> bool:
        """Set up the testing environment with models and test data."""
        try:
            # Set up default models
            model_setup = self.model_manager.setup_default_models()
            
            if "primary_model" not in model_setup:
                logger.error("Failed to set up primary model")
                return False
            
            # Load the model into detection engine
            primary_model_path = model_setup["primary_model"]
            self.detection_engine.load_model(primary_model_path)
            
            # Create test image directories
            for cat_type in self.cat_types:
                for env in self.environments:
                    test_dir = self.test_images_dir / cat_type / env
                    test_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info("Test environment setup complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set up test environment: {e}")
            return False
    
    def create_synthetic_test_images(self) -> None:
        """Create synthetic test images for development testing."""
        if not OPENCV_AVAILABLE:
            logger.warning("OpenCV not available - cannot create synthetic images")
            return
        
        try:
            # Create synthetic images for testing
            for cat_type in self.cat_types:
                for env in self.environments:
                    test_dir = self.test_images_dir / cat_type / env
                    
                    # Create a few synthetic test images
                    for i in range(3):
                        # Create base image based on environment
                        if env == "black_counter":
                            base_color = (20, 20, 20)  # Dark background
                        elif env == "wood_floor":
                            base_color = (139, 115, 85)  # Wood color
                        else:
                            base_color = (100, 100, 100)  # Mixed
                        
                        # Create 640x480 image
                        img = np.full((480, 640, 3), base_color, dtype=np.uint8)
                        
                        # Add synthetic "cat" shape based on type
                        if cat_type == "lynx_point":
                            cat_color = (240, 240, 220)  # Light colored
                        elif cat_type == "tabby":
                            cat_color = (101, 67, 33)   # Brown
                        else:
                            cat_color = (150, 150, 150)  # Mixed
                        
                        # Draw a simple cat-like shape
                        center_x, center_y = 320, 240
                        cv2.ellipse(img, (center_x, center_y), (80, 40), 0, 0, 360, cat_color, -1)
                        cv2.circle(img, (center_x - 20, center_y - 20), 15, cat_color, -1)  # Head
                        cv2.circle(img, (center_x + 20, center_y + 30), 10, cat_color, -1)   # Tail
                        
                        # Add some noise
                        noise = np.random.randint(-20, 20, img.shape, dtype=np.int16)
                        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
                        
                        # Save image
                        filename = f"synthetic_{cat_type}_{env}_{i}.jpg"
                        filepath = test_dir / filename
                        cv2.imwrite(str(filepath), img)
            
            logger.info("Synthetic test images created")
            
        except Exception as e:
            logger.error(f"Failed to create synthetic test images: {e}")
    
    def test_detection_accuracy(self, cat_type: str, environment: str) -> Dict[str, Any]:
        """Test detection accuracy for a specific cat type and environment."""
        test_dir = self.test_images_dir / cat_type / environment
        
        if not test_dir.exists():
            logger.warning(f"Test directory not found: {test_dir}")
            return {"error": "Test directory not found"}
        
        results = {
            "cat_type": cat_type,
            "environment": environment,
            "total_images": 0,
            "detections_found": 0,
            "confidence_scores": [],
            "detection_details": []
        }
        
        try:
            # Get all image files
            image_files = list(test_dir.glob("*.jpg")) + list(test_dir.glob("*.png"))
            results["total_images"] = len(image_files)
            
            if not image_files:
                logger.warning(f"No test images found in {test_dir}")
                return results
            
            # Test each image
            for img_path in image_files:
                try:
                    # Load image
                    img = cv2.imread(str(img_path))
                    if img is None:
                        continue
                    
                    # Run detection
                    detections = self.detection_engine.detect_cats(img)
                    
                    if detections:
                        results["detections_found"] += 1
                        
                        # Collect confidence scores
                        for detection in detections:
                            for bbox in detection.bounding_boxes:
                                results["confidence_scores"].append(bbox.confidence)
                        
                        # Store detection details
                        detection_info = {
                            "image": img_path.name,
                            "detection_count": len(detections),
                            "max_confidence": max(bbox.confidence for det in detections for bbox in det.bounding_boxes),
                            "bounding_boxes": [
                                {
                                    "x": bbox.x, "y": bbox.y, 
                                    "width": bbox.width, "height": bbox.height,
                                    "confidence": bbox.confidence
                                }
                                for det in detections for bbox in det.bounding_boxes
                            ]
                        }
                        results["detection_details"].append(detection_info)
                
                except Exception as e:
                    logger.warning(f"Error processing {img_path}: {e}")
            
            # Calculate statistics
            if results["confidence_scores"]:
                results["avg_confidence"] = sum(results["confidence_scores"]) / len(results["confidence_scores"])
                results["min_confidence"] = min(results["confidence_scores"])
                results["max_confidence"] = max(results["confidence_scores"])
            else:
                results["avg_confidence"] = 0.0
                results["min_confidence"] = 0.0
                results["max_confidence"] = 0.0
            
            results["detection_rate"] = results["detections_found"] / results["total_images"] if results["total_images"] > 0 else 0.0
            
            logger.info(f"Detection test complete for {cat_type} on {environment}: "
                       f"{results['detection_rate']:.2%} detection rate")
            
            return results
            
        except Exception as e:
            logger.error(f"Error during detection testing: {e}")
            results["error"] = str(e)
            return results
    
    def fine_tune_parameters(self) -> Dict[str, Any]:
        """Fine-tune detection parameters for optimal performance."""
        best_params = {
            "confidence_threshold": 0.7,
            "nms_threshold": 0.4,
            "overall_score": 0.0
        }
        
        tuning_results = []
        
        try:
            # Test different parameter combinations
            for conf_thresh in self.confidence_thresholds:
                for nms_thresh in self.nms_thresholds:
                    # Set parameters
                    self.detection_engine.set_confidence_threshold(conf_thresh)
                    if hasattr(self.detection_engine, 'nms_threshold'):
                        self.detection_engine.nms_threshold = nms_thresh
                    
                    # Test on all cat types and environments
                    total_score = 0.0
                    test_count = 0
                    
                    for cat_type in self.cat_types:
                        for env in self.environments:
                            test_result = self.test_detection_accuracy(cat_type, env)
                            
                            if "error" not in test_result:
                                # Score based on detection rate and confidence
                                detection_rate = test_result.get("detection_rate", 0.0)
                                avg_confidence = test_result.get("avg_confidence", 0.0)
                                
                                # Weighted score (favor detection rate over confidence)
                                score = 0.7 * detection_rate + 0.3 * avg_confidence
                                total_score += score
                                test_count += 1
                    
                    # Calculate overall score
                    overall_score = total_score / test_count if test_count > 0 else 0.0
                    
                    result = {
                        "confidence_threshold": conf_thresh,
                        "nms_threshold": nms_thresh,
                        "overall_score": overall_score,
                        "test_count": test_count
                    }
                    
                    tuning_results.append(result)
                    
                    # Update best parameters
                    if overall_score > best_params["overall_score"]:
                        best_params.update(result)
                    
                    logger.info(f"Tested conf={conf_thresh}, nms={nms_thresh}, score={overall_score:.3f}")
            
            # Apply best parameters
            self.detection_engine.set_confidence_threshold(best_params["confidence_threshold"])
            if hasattr(self.detection_engine, 'nms_threshold'):
                self.detection_engine.nms_threshold = best_params["nms_threshold"]
            
            logger.info(f"Fine-tuning complete. Best parameters: {best_params}")
            
            return {
                "best_parameters": best_params,
                "all_results": tuning_results,
                "tuning_complete": True
            }
            
        except Exception as e:
            logger.error(f"Error during parameter fine-tuning: {e}")
            return {"error": str(e), "tuning_complete": False}
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive testing for all cat types and environments."""
        logger.info("Starting comprehensive cat detection test")
        
        # Set up test environment
        if not self.setup_test_environment():
            return {"error": "Failed to set up test environment"}
        
        # Create synthetic test images if none exist
        self.create_synthetic_test_images()
        
        comprehensive_results = {
            "test_timestamp": datetime.now().isoformat(),
            "model_info": self.detection_engine.get_model_info(),
            "test_results": {},
            "fine_tuning_results": {},
            "summary": {}
        }
        
        try:
            # Test all combinations
            for cat_type in self.cat_types:
                comprehensive_results["test_results"][cat_type] = {}
                
                for env in self.environments:
                    test_result = self.test_detection_accuracy(cat_type, env)
                    comprehensive_results["test_results"][cat_type][env] = test_result
            
            # Fine-tune parameters
            tuning_results = self.fine_tune_parameters()
            comprehensive_results["fine_tuning_results"] = tuning_results
            
            # Generate summary
            summary = self._generate_test_summary(comprehensive_results["test_results"])
            comprehensive_results["summary"] = summary
            
            # Save results
            results_file = self.test_images_dir / f"detection_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(results_file, 'w') as f:
                json.dump(comprehensive_results, f, indent=2, default=str)
            
            logger.info(f"Comprehensive test complete. Results saved to {results_file}")
            
            return comprehensive_results
            
        except Exception as e:
            logger.error(f"Error during comprehensive testing: {e}")
            comprehensive_results["error"] = str(e)
            return comprehensive_results
    
    def _generate_test_summary(self, test_results: Dict[str, Dict[str, Dict]]) -> Dict[str, Any]:
        """Generate a summary of test results."""
        summary = {
            "overall_detection_rate": 0.0,
            "cat_type_performance": {},
            "environment_performance": {},
            "recommendations": []
        }
        
        try:
            total_rate = 0.0
            total_tests = 0
            
            # Analyze by cat type
            for cat_type, env_results in test_results.items():
                cat_rates = []
                for env, result in env_results.items():
                    if "detection_rate" in result:
                        rate = result["detection_rate"]
                        cat_rates.append(rate)
                        total_rate += rate
                        total_tests += 1
                
                if cat_rates:
                    summary["cat_type_performance"][cat_type] = {
                        "avg_detection_rate": sum(cat_rates) / len(cat_rates),
                        "best_environment": max(env_results.items(), key=lambda x: x[1].get("detection_rate", 0))[0],
                        "worst_environment": min(env_results.items(), key=lambda x: x[1].get("detection_rate", 0))[0]
                    }
            
            # Analyze by environment
            env_rates = {}
            for cat_type, env_results in test_results.items():
                for env, result in env_results.items():
                    if env not in env_rates:
                        env_rates[env] = []
                    if "detection_rate" in result:
                        env_rates[env].append(result["detection_rate"])
            
            for env, rates in env_rates.items():
                if rates:
                    summary["environment_performance"][env] = {
                        "avg_detection_rate": sum(rates) / len(rates),
                        "consistency": 1.0 - (max(rates) - min(rates))  # Higher is more consistent
                    }
            
            # Overall detection rate
            summary["overall_detection_rate"] = total_rate / total_tests if total_tests > 0 else 0.0
            
            # Generate recommendations
            if summary["overall_detection_rate"] < 0.7:
                summary["recommendations"].append("Consider lowering confidence threshold for better detection rate")
            
            if summary["cat_type_performance"]:
                worst_cat_type = min(summary["cat_type_performance"].items(), 
                                   key=lambda x: x[1]["avg_detection_rate"])
                if worst_cat_type[1]["avg_detection_rate"] < 0.5:
                    summary["recommendations"].append(f"Poor detection for {worst_cat_type[0]} - consider model fine-tuning")
            
            if summary["environment_performance"]:
                worst_env = min(summary["environment_performance"].items(),
                              key=lambda x: x[1]["avg_detection_rate"])
                if worst_env[1]["avg_detection_rate"] < 0.5:
                    summary["recommendations"].append(f"Poor detection in {worst_env[0]} - consider lighting adjustments")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating test summary: {e}")
            return {"error": str(e)}
    
    def test_real_time_performance(self, duration_seconds: int = 30) -> Dict[str, Any]:
        """Test real-time detection performance."""
        logger.info(f"Starting {duration_seconds}s real-time performance test")
        
        performance_results = {
            "test_duration": duration_seconds,
            "frames_processed": 0,
            "detections_found": 0,
            "avg_fps": 0.0,
            "avg_detection_time": 0.0,
            "model_used": self.detection_engine.get_current_model(),
            "errors": []
        }
        
        try:
            import time
            start_time = time.time()
            detection_times = []
            
            # Create a test frame (synthetic)
            if OPENCV_AVAILABLE:
                test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            else:
                test_frame = [[0] * 640] * 480  # Mock frame
            
            while time.time() - start_time < duration_seconds:
                try:
                    frame_start = time.time()
                    
                    # Run detection
                    detections = self.detection_engine.detect_cats(test_frame)
                    
                    frame_end = time.time()
                    detection_time = frame_end - frame_start
                    detection_times.append(detection_time)
                    
                    performance_results["frames_processed"] += 1
                    if detections:
                        performance_results["detections_found"] += 1
                    
                    # Small delay to prevent overwhelming the system
                    time.sleep(0.1)
                    
                except Exception as e:
                    performance_results["errors"].append(str(e))
            
            # Calculate statistics
            total_time = time.time() - start_time
            if performance_results["frames_processed"] > 0:
                performance_results["avg_fps"] = performance_results["frames_processed"] / total_time
                performance_results["avg_detection_time"] = sum(detection_times) / len(detection_times)
            
            logger.info(f"Performance test complete: {performance_results['avg_fps']:.2f} FPS, "
                       f"{performance_results['avg_detection_time']*1000:.1f}ms per detection")
            
            return performance_results
            
        except Exception as e:
            logger.error(f"Error during performance testing: {e}")
            performance_results["error"] = str(e)
            return performance_results


def main():
    """Main function for running cat detection tests."""
    logging.basicConfig(level=logging.INFO)
    
    tester = CatDetectionTester()
    
    # Run comprehensive test
    results = tester.run_comprehensive_test()
    
    if "error" not in results:
        print("=== Cat Detection Test Results ===")
        print(f"Overall Detection Rate: {results['summary']['overall_detection_rate']:.2%}")
        
        print("\nCat Type Performance:")
        for cat_type, perf in results['summary']['cat_type_performance'].items():
            print(f"  {cat_type}: {perf['avg_detection_rate']:.2%}")
        
        print("\nEnvironment Performance:")
        for env, perf in results['summary']['environment_performance'].items():
            print(f"  {env}: {perf['avg_detection_rate']:.2%}")
        
        if results['summary']['recommendations']:
            print("\nRecommendations:")
            for rec in results['summary']['recommendations']:
                print(f"  - {rec}")
        
        # Run performance test
        print("\n=== Performance Test ===")
        perf_results = tester.test_real_time_performance(10)
        print(f"Average FPS: {perf_results['avg_fps']:.2f}")
        print(f"Average Detection Time: {perf_results['avg_detection_time']*1000:.1f}ms")
        print(f"Model Used: {perf_results['model_used']}")
    else:
        print(f"Test failed: {results['error']}")


if __name__ == "__main__":
    main()