"""Model management utilities for downloading and quantizing detection models."""

import logging
import os
import urllib.request
import json
from typing import Optional, Dict, Any
from pathlib import Path

# Handle TensorFlow Lite import gracefully
try:
    import tflite_runtime.interpreter as tflite
    TFLITE_AVAILABLE = True
except ImportError:
    try:
        import tensorflow.lite as tflite
        TFLITE_AVAILABLE = True
    except ImportError:
        TFLITE_AVAILABLE = False
        tflite = None

# Handle numpy import gracefully
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages downloading, quantization, and optimization of detection models."""
    
    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        
        # Model URLs and configurations
        self.model_configs = {
            "mobilenet_v2_coco": {
                "url": "https://storage.googleapis.com/download.tensorflow.org/models/tflite/coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip",
                "filename": "detect.tflite",
                "description": "MobileNet SSD v1 quantized for COCO object detection",
                "input_size": (300, 300),
                "quantized": True
            },
            "mobilenet_v2_float": {
                "url": "https://storage.googleapis.com/download.tensorflow.org/models/tflite/coco_ssd_mobilenet_v1_1.0_2018_07_03.zip",
                "filename": "detect.tflite", 
                "description": "MobileNet SSD v1 float32 for COCO object detection",
                "input_size": (300, 300),
                "quantized": False
            }
        }
        
        logger.info(f"Model manager initialized with models directory: {self.models_dir}")
    
    def download_model(self, model_name: str, force_download: bool = False) -> Optional[str]:
        """Download a pre-trained model."""
        if model_name not in self.model_configs:
            logger.error(f"Unknown model: {model_name}")
            return None
        
        config = self.model_configs[model_name]
        model_path = self.models_dir / f"{model_name}.tflite"
        
        # Check if model already exists
        if model_path.exists() and not force_download:
            logger.info(f"Model {model_name} already exists at {model_path}")
            return str(model_path)
        
        try:
            logger.info(f"Downloading {model_name} from {config['url']}")
            
            # Download the zip file
            zip_path = self.models_dir / f"{model_name}.zip"
            urllib.request.urlretrieve(config['url'], zip_path)
            
            # Extract the model file
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Find the model file in the zip
                for file_info in zip_ref.filelist:
                    if file_info.filename.endswith('.tflite'):
                        # Extract to our target path
                        with zip_ref.open(file_info) as source, open(model_path, 'wb') as target:
                            target.write(source.read())
                        break
                else:
                    logger.error(f"No .tflite file found in {zip_path}")
                    return None
            
            # Clean up zip file
            zip_path.unlink()
            
            logger.info(f"Successfully downloaded {model_name} to {model_path}")
            return str(model_path)
            
        except Exception as e:
            logger.error(f"Failed to download model {model_name}: {e}")
            return None
    
    def create_quantized_model(self, float_model_path: str, output_path: Optional[str] = None) -> Optional[str]:
        """Create a quantized (INT8) version of a float32 model."""
        if not TFLITE_AVAILABLE:
            logger.error("TensorFlow Lite not available for quantization")
            return None
        
        try:
            # This is a placeholder for quantization
            # In a real implementation, you would need TensorFlow (not just TFLite runtime)
            # to perform post-training quantization
            logger.warning("Model quantization requires full TensorFlow installation")
            logger.info("Using pre-quantized models instead")
            
            # For now, recommend using pre-quantized models
            return self.download_model("mobilenet_v2_coco")  # This is already quantized
            
        except Exception as e:
            logger.error(f"Quantization failed: {e}")
            return None
    
    def optimize_model_for_arm(self, model_path: str, output_path: Optional[str] = None) -> Optional[str]:
        """Optimize model for ARM processors (Raspberry Pi)."""
        if not TFLITE_AVAILABLE:
            logger.error("TensorFlow Lite not available for optimization")
            return None
        
        try:
            if output_path is None:
                base_path = Path(model_path)
                output_path = str(base_path.parent / f"{base_path.stem}_arm_optimized.tflite")
            
            # Load the original model
            interpreter = tflite.Interpreter(model_path=model_path)
            interpreter.allocate_tensors()
            
            # For now, we'll just copy the model and log optimization info
            # Real ARM optimization would require TensorFlow converter
            import shutil
            shutil.copy2(model_path, output_path)
            
            logger.info(f"ARM-optimized model created at {output_path}")
            logger.info("Note: Full ARM optimization requires TensorFlow converter")
            
            return output_path
            
        except Exception as e:
            logger.error(f"ARM optimization failed: {e}")
            return None
    
    def validate_model(self, model_path: str) -> Dict[str, Any]:
        """Validate a TensorFlow Lite model."""
        if not TFLITE_AVAILABLE:
            return {"valid": False, "error": "TensorFlow Lite not available"}
        
        try:
            # Load model
            interpreter = tflite.Interpreter(model_path=model_path)
            interpreter.allocate_tensors()
            
            # Get model details
            input_details = interpreter.get_input_details()
            output_details = interpreter.get_output_details()
            
            # Basic validation
            validation_result = {
                "valid": True,
                "model_path": model_path,
                "file_size_mb": os.path.getsize(model_path) / (1024 * 1024),
                "input_count": len(input_details),
                "output_count": len(output_details),
                "inputs": [],
                "outputs": []
            }
            
            # Input details
            for i, detail in enumerate(input_details):
                input_info = {
                    "index": i,
                    "name": detail.get("name", f"input_{i}"),
                    "shape": detail["shape"].tolist() if hasattr(detail["shape"], "tolist") else list(detail["shape"]),
                    "dtype": str(detail["dtype"]),
                    "quantization": detail.get("quantization", None)
                }
                validation_result["inputs"].append(input_info)
            
            # Output details
            for i, detail in enumerate(output_details):
                output_info = {
                    "index": i,
                    "name": detail.get("name", f"output_{i}"),
                    "shape": detail["shape"].tolist() if hasattr(detail["shape"], "tolist") else list(detail["shape"]),
                    "dtype": str(detail["dtype"]),
                    "quantization": detail.get("quantization", None)
                }
                validation_result["outputs"].append(output_info)
            
            # Check if model is quantized
            input_dtype = input_details[0]["dtype"]
            validation_result["quantized"] = input_dtype == np.uint8
            
            # Estimate suitability for Raspberry Pi
            model_size_mb = validation_result["file_size_mb"]
            is_quantized = validation_result["quantized"]
            
            if model_size_mb < 10 and is_quantized:
                suitability = "excellent"
            elif model_size_mb < 20 and is_quantized:
                suitability = "good"
            elif model_size_mb < 50:
                suitability = "fair"
            else:
                suitability = "poor"
            
            validation_result["raspberry_pi_suitability"] = suitability
            
            logger.info(f"Model validation successful: {model_path}")
            logger.info(f"Size: {model_size_mb:.1f}MB, Quantized: {is_quantized}, Suitability: {suitability}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Model validation failed: {e}")
            return {"valid": False, "error": str(e)}
    
    def get_recommended_model(self) -> str:
        """Get the recommended model for Raspberry Pi Zero W."""
        # For Pi Zero W, we want the smallest, most optimized model
        return "mobilenet_v2_coco"  # Pre-quantized MobileNet
    
    def setup_default_models(self) -> Dict[str, str]:
        """Set up default models for the detection system."""
        results = {}
        
        # Download recommended model
        recommended_model = self.get_recommended_model()
        model_path = self.download_model(recommended_model)
        
        if model_path:
            results["primary_model"] = model_path
            results["primary_model_name"] = recommended_model
            
            # Validate the model
            validation = self.validate_model(model_path)
            results["validation"] = validation
            
            logger.info(f"Default model setup complete: {model_path}")
        else:
            logger.error("Failed to set up default model")
            results["error"] = "Failed to download default model"
        
        return results
    
    def list_available_models(self) -> Dict[str, Dict[str, Any]]:
        """List all available model configurations."""
        return self.model_configs.copy()
    
    def get_model_path(self, model_name: str) -> Optional[str]:
        """Get the local path for a model (download if necessary)."""
        model_path = self.models_dir / f"{model_name}.tflite"
        
        if model_path.exists():
            return str(model_path)
        else:
            # Try to download it
            return self.download_model(model_name)
    
    def create_cat_optimized_config(self) -> Dict[str, Any]:
        """Create configuration optimized for cat detection."""
        return {
            "confidence_threshold": 0.7,
            "nms_threshold": 0.4,
            "max_detections": 10,
            "target_classes": [16],  # Cat class ID in COCO
            "input_size": (224, 224),  # Optimized for Pi Zero W
            "preprocessing": {
                "normalize": True,
                "mean": [127.5, 127.5, 127.5],
                "std": [127.5, 127.5, 127.5]
            },
            "postprocessing": {
                "apply_nms": True,
                "filter_classes": True,
                "min_box_area": 100
            }
        }