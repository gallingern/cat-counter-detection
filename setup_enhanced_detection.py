#!/usr/bin/env python3
"""Setup script for enhanced detection with model download and testing."""

import sys
import os
import logging
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cat_counter_detection.services.model_manager import ModelManager
from cat_counter_detection.services.enhanced_detection_engine import EnhancedCatDetectionEngine
from cat_counter_detection.cat_detection_tester import CatDetectionTester

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def setup_models():
    """Download and set up detection models."""
    print("=== Setting up Enhanced Detection Models ===\n")
    
    # Initialize model manager
    model_manager = ModelManager()
    
    # Try to download the recommended model
    print("1. Downloading recommended model for Raspberry Pi Zero W...")
    recommended_model = model_manager.get_recommended_model()
    print(f"   Recommended model: {recommended_model}")
    
    try:
        model_path = model_manager.download_model(recommended_model)
        if model_path:
            print(f"   ✓ Model downloaded successfully: {model_path}")
            
            # Validate the model
            print("2. Validating downloaded model...")
            validation = model_manager.validate_model(model_path)
            
            if validation["valid"]:
                print("   ✓ Model validation successful")
                print(f"   - File size: {validation['file_size_mb']:.1f} MB")
                print(f"   - Quantized: {validation['quantized']}")
                print(f"   - Raspberry Pi suitability: {validation['raspberry_pi_suitability']}")
                print(f"   - Input count: {validation['input_count']}")
                print(f"   - Output count: {validation['output_count']}")
                
                # Show input/output details
                for inp in validation["inputs"]:
                    print(f"   - Input: {inp['name']} {inp['shape']} ({inp['dtype']})")
                
                return model_path
            else:
                print(f"   ✗ Model validation failed: {validation.get('error', 'Unknown error')}")
                return None
        else:
            print("   ✗ Model download failed")
            return None
            
    except Exception as e:
        print(f"   ✗ Error during model setup: {e}")
        return None


def test_enhanced_detection_with_model(model_path):
    """Test enhanced detection with the downloaded model."""
    print("\n=== Testing Enhanced Detection ===\n")
    
    try:
        # Initialize enhanced detection engine
        engine = EnhancedCatDetectionEngine()
        
        print("1. Loading model into detection engine...")
        engine.load_model(model_path)
        
        model_info = engine.get_model_info()
        print(f"   - Current model: {model_info['current_model']}")
        print(f"   - Primary model loaded: {model_info['primary_model_loaded']}")
        print(f"   - Fallback model loaded: {model_info['fallback_model_loaded']}")
        
        # Apply Raspberry Pi optimizations
        print("2. Applying Raspberry Pi Zero W optimizations...")
        opt_result = engine.optimize_for_raspberry_pi_zero_w()
        
        if opt_result["success"]:
            print("   ✓ Optimizations applied successfully")
            for opt in opt_result["optimizations_applied"]:
                print(f"     - {opt}")
        else:
            print(f"   ✗ Optimization failed: {opt_result.get('error', 'Unknown error')}")
        
        # Test detection performance
        print("3. Testing detection performance...")
        import numpy as np
        import time
        
        # Create test frames
        test_frames = []
        for i in range(10):
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            test_frames.append(frame)
        
        # Time detection performance
        start_time = time.time()
        total_detections = 0
        
        for frame in test_frames:
            detections = engine.detect_cats(frame)
            total_detections += len(detections)
        
        end_time = time.time()
        
        avg_time_per_frame = (end_time - start_time) / len(test_frames)
        fps = 1.0 / avg_time_per_frame if avg_time_per_frame > 0 else 0
        
        print(f"   - Average time per frame: {avg_time_per_frame*1000:.1f}ms")
        print(f"   - Estimated FPS: {fps:.2f}")
        print(f"   - Total detections: {total_detections}")
        print(f"   - Model used: {engine.get_current_model()}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Detection testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_comprehensive_cat_detection_test():
    """Run comprehensive testing for cat detection accuracy."""
    print("\n=== Comprehensive Cat Detection Testing ===\n")
    
    try:
        # Initialize tester
        tester = CatDetectionTester()
        
        print("1. Setting up test environment...")
        if not tester.setup_test_environment():
            print("   ✗ Test environment setup failed")
            return False
        
        print("   ✓ Test environment ready")
        
        # Create synthetic test images
        print("2. Creating synthetic test images...")
        tester.create_synthetic_test_images()
        print("   ✓ Synthetic test images created")
        
        # Test detection accuracy for different cat types and environments
        print("3. Testing detection accuracy...")
        
        test_results = {}
        cat_types = ["lynx_point", "tabby", "mixed"]
        environments = ["black_counter", "wood_floor", "mixed_lighting"]
        
        for cat_type in cat_types:
            test_results[cat_type] = {}
            for env in environments:
                print(f"   Testing {cat_type} on {env}...")
                result = tester.test_detection_accuracy(cat_type, env)
                
                if "error" not in result:
                    test_results[cat_type][env] = result
                    print(f"     - Detection rate: {result['detection_rate']:.2%}")
                    print(f"     - Average confidence: {result['avg_confidence']:.3f}")
                else:
                    print(f"     ✗ Test failed: {result['error']}")
        
        # Generate summary
        print("4. Test Summary:")
        total_tests = 0
        successful_tests = 0
        total_detection_rate = 0.0
        
        for cat_type, env_results in test_results.items():
            print(f"   {cat_type.replace('_', ' ').title()}:")
            for env, result in env_results.items():
                if "detection_rate" in result:
                    rate = result["detection_rate"]
                    total_detection_rate += rate
                    total_tests += 1
                    if rate > 0:
                        successful_tests += 1
                    print(f"     - {env.replace('_', ' ').title()}: {rate:.2%}")
        
        if total_tests > 0:
            avg_detection_rate = total_detection_rate / total_tests
            print(f"\n   Overall Results:")
            print(f"   - Average detection rate: {avg_detection_rate:.2%}")
            print(f"   - Tests with detections: {successful_tests}/{total_tests}")
        
        # Fine-tune parameters if needed
        if total_tests > 0 and avg_detection_rate < 0.5:
            print("5. Fine-tuning detection parameters...")
            tuning_result = tester.fine_tune_parameters()
            
            if tuning_result.get("tuning_complete"):
                best_params = tuning_result["best_parameters"]
                print("   ✓ Parameter fine-tuning complete")
                print(f"     - Best confidence threshold: {best_params['confidence_threshold']}")
                print(f"     - Best NMS threshold: {best_params['nms_threshold']}")
                print(f"     - Best overall score: {best_params['overall_score']:.3f}")
            else:
                print("   ✗ Parameter fine-tuning failed")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Comprehensive testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main setup function."""
    print("Enhanced Cat Detection Setup and Testing")
    print("=" * 50)
    
    try:
        # Step 1: Set up models
        model_path = setup_models()
        
        if model_path:
            # Step 2: Test enhanced detection
            if test_enhanced_detection_with_model(model_path):
                # Step 3: Run comprehensive testing
                run_comprehensive_cat_detection_test()
            else:
                print("Enhanced detection testing failed, skipping comprehensive tests")
        else:
            print("Model setup failed, testing with fallback models only")
            # Still run comprehensive testing with fallback
            run_comprehensive_cat_detection_test()
        
        print("\n" + "=" * 50)
        print("Setup and testing complete!")
        print("\nNext steps:")
        print("1. Review test results and detection accuracy")
        print("2. Adjust confidence thresholds if needed")
        print("3. Test with real cat images if available")
        print("4. Deploy to Raspberry Pi Zero W for real-world testing")
        
    except KeyboardInterrupt:
        print("\nSetup interrupted by user")
    except Exception as e:
        print(f"\nSetup failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()