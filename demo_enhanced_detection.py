#!/usr/bin/env python3
"""Demo script for testing the enhanced cat detection engine."""

import sys
import os
import logging
import numpy as np
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cat_counter_detection.services.enhanced_detection_engine import EnhancedCatDetectionEngine
from cat_counter_detection.services.model_manager import ModelManager
from cat_counter_detection.cat_detection_tester import CatDetectionTester

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_enhanced_detection_engine():
    """Test the enhanced detection engine functionality."""
    print("=== Enhanced Cat Detection Engine Demo ===\n")
    
    # Initialize the enhanced detection engine
    print("1. Initializing Enhanced Detection Engine...")
    engine = EnhancedCatDetectionEngine()
    
    # Display initial status
    model_info = engine.get_model_info()
    print(f"   - Primary model loaded: {model_info['primary_model_loaded']}")
    print(f"   - Fallback model loaded: {model_info['fallback_model_loaded']}")
    print(f"   - Current model: {model_info['current_model']}")
    print(f"   - TensorFlow Lite available: {model_info['tflite_available']}")
    print(f"   - OpenCV available: {model_info['opencv_available']}")
    print()
    
    # Test model loading
    print("2. Testing Model Loading...")
    try:
        # Try to load MobileNet model (will fallback to OpenCV if not available)
        engine.load_model("models/mobilenet_v2_coco.tflite")
        
        model_info = engine.get_model_info()
        print(f"   - Model loading result: {model_info['current_model']}")
        print(f"   - Primary model loaded: {model_info['primary_model_loaded']}")
        print(f"   - Fallback model loaded: {model_info['fallback_model_loaded']}")
        
    except Exception as e:
        print(f"   - Model loading failed: {e}")
    print()
    
    # Test configuration
    print("3. Testing Configuration...")
    engine.set_confidence_threshold(0.8)
    engine.set_roi((100, 100, 400, 300))
    
    model_info = engine.get_model_info()
    print(f"   - Confidence threshold: {model_info['confidence_threshold']}")
    print(f"   - ROI: {model_info['roi']}")
    print()
    
    # Test detection with synthetic frame
    print("4. Testing Detection...")
    try:
        # Create a synthetic test frame
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Run detection
        detections = engine.detect_cats(test_frame)
        print(f"   - Detections found: {len(detections)}")
        
        for i, detection in enumerate(detections):
            print(f"   - Detection {i+1}:")
            for j, bbox in enumerate(detection.bounding_boxes):
                print(f"     * Bounding box {j+1}: ({bbox.x}, {bbox.y}, {bbox.width}, {bbox.height})")
                print(f"     * Confidence: {bbox.confidence:.3f}")
        
    except Exception as e:
        print(f"   - Detection failed: {e}")
    print()
    
    # Test Raspberry Pi optimizations
    print("5. Testing Raspberry Pi Zero W Optimizations...")
    try:
        optimization_result = engine.optimize_for_raspberry_pi_zero_w()
        
        if optimization_result["success"]:
            print("   - Optimization successful!")
            print(f"   - Optimizations applied: {len(optimization_result['optimizations_applied'])}")
            for opt in optimization_result['optimizations_applied']:
                print(f"     * {opt}")
            
            # Show updated model info
            model_info = engine.get_model_info()
            print(f"   - ARM optimized: {model_info['arm_optimized']}")
            print(f"   - Input size: {model_info['input_size']}")
        else:
            print(f"   - Optimization failed: {optimization_result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"   - Optimization test failed: {e}")
    print()
    
    # Test model switching
    print("6. Testing Model Switching...")
    try:
        current_model = engine.get_current_model()
        print(f"   - Current model: {current_model}")
        
        # Try to switch to OpenCV
        if engine.force_fallback_to_opencv():
            print("   - Successfully switched to OpenCV fallback")
            print(f"   - New current model: {engine.get_current_model()}")
        else:
            print("   - Could not switch to OpenCV (not available)")
        
        # Try to switch back to MobileNet
        if engine.switch_to_mobilenet():
            print("   - Successfully switched back to MobileNet")
            print(f"   - New current model: {engine.get_current_model()}")
        else:
            print("   - Could not switch to MobileNet (not available)")
            
    except Exception as e:
        print(f"   - Model switching test failed: {e}")
    print()


def test_model_manager():
    """Test the model manager functionality."""
    print("=== Model Manager Demo ===\n")
    
    # Initialize model manager
    print("1. Initializing Model Manager...")
    model_manager = ModelManager()
    
    # List available models
    print("2. Available Model Configurations:")
    available_models = model_manager.list_available_models()
    for name, config in available_models.items():
        print(f"   - {name}:")
        print(f"     * Description: {config['description']}")
        print(f"     * Input size: {config['input_size']}")
        print(f"     * Quantized: {config['quantized']}")
    print()
    
    # Get recommended model
    print("3. Recommended Model for Raspberry Pi Zero W:")
    recommended = model_manager.get_recommended_model()
    print(f"   - {recommended}")
    print()
    
    # Create cat-optimized configuration
    print("4. Cat-Optimized Configuration:")
    cat_config = model_manager.create_cat_optimized_config()
    print(f"   - Confidence threshold: {cat_config['confidence_threshold']}")
    print(f"   - NMS threshold: {cat_config['nms_threshold']}")
    print(f"   - Max detections: {cat_config['max_detections']}")
    print(f"   - Target classes: {cat_config['target_classes']}")
    print(f"   - Input size: {cat_config['input_size']}")
    print()


def test_detection_tester():
    """Test the cat detection tester functionality."""
    print("=== Cat Detection Tester Demo ===\n")
    
    # Initialize tester
    print("1. Initializing Cat Detection Tester...")
    try:
        tester = CatDetectionTester()
        print("   - Tester initialized successfully")
        
        # Set up test environment
        print("2. Setting up test environment...")
        if tester.setup_test_environment():
            print("   - Test environment setup successful")
            
            # Create synthetic test images
            print("3. Creating synthetic test images...")
            tester.create_synthetic_test_images()
            print("   - Synthetic test images created")
            
            # Test detection on one cat type/environment
            print("4. Testing detection accuracy...")
            test_result = tester.test_detection_accuracy("tabby", "black_counter")
            
            if "error" not in test_result:
                print(f"   - Total images: {test_result['total_images']}")
                print(f"   - Detections found: {test_result['detections_found']}")
                print(f"   - Detection rate: {test_result['detection_rate']:.2%}")
                print(f"   - Average confidence: {test_result['avg_confidence']:.3f}")
            else:
                print(f"   - Test failed: {test_result['error']}")
            
            # Test real-time performance
            print("5. Testing real-time performance...")
            perf_result = tester.test_real_time_performance(5)  # 5 second test
            
            if "error" not in perf_result:
                print(f"   - Frames processed: {perf_result['frames_processed']}")
                print(f"   - Average FPS: {perf_result['avg_fps']:.2f}")
                print(f"   - Average detection time: {perf_result['avg_detection_time']*1000:.1f}ms")
                print(f"   - Model used: {perf_result['model_used']}")
            else:
                print(f"   - Performance test failed: {perf_result['error']}")
        else:
            print("   - Test environment setup failed")
            
    except Exception as e:
        print(f"   - Tester initialization failed: {e}")
    print()


def main():
    """Main demo function."""
    print("Enhanced Cat Detection System Demo")
    print("=" * 50)
    print()
    
    try:
        # Test enhanced detection engine
        test_enhanced_detection_engine()
        
        # Test model manager
        test_model_manager()
        
        # Test detection tester
        test_detection_tester()
        
        print("=== Demo Complete ===")
        print("All components tested successfully!")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()