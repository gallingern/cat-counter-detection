"""Enhanced cat detection engine with MobileNetV2 and model fallback."""

import logging
import os
import json
from typing import List, Tuple, Optional, Any, Dict
from datetime import datetime
from ..models.detection import Detection, BoundingBox
from .interfaces import DetectionEngineInterface
from .detection_engine import CatDetectionEngine

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

# Handle OpenCV import gracefully
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    cv2 = None
    np = None

logger = logging.getLogger(__name__)


class EnhancedCatDetectionEngine(DetectionEngineInterface):
    """Enhanced cat detection engine with MobileNetV2 and fallback to OpenCV."""
    
    def __init__(self):
        # Model management
        self.primary_model_loaded = False
        self.fallback_model_loaded = False
        self.current_model = "none"
        
        # TensorFlow Lite interpreter
        self.tflite_interpreter = None
        self.input_details = None
        self.output_details = None
        
        # OpenCV fallback engine
        self.opencv_engine = CatDetectionEngine()
        
        # Detection parameters
        self.confidence_threshold = 0.7
        self.roi = (0, 0, 640, 480)
        self.input_size = (224, 224)  # MobileNetV2 standard input size
        
        # Model paths
        self.mobilenet_model_path = None
        self.opencv_model_path = None
        
        # Performance optimization flags
        self.quantized_model = False
        self.arm_optimized = False
        
        # Cat-specific class IDs for COCO dataset (used by MobileNet models)
        self.cat_class_id = 16  # Cat class in COCO dataset
        
        # Detection post-processing parameters
        self.nms_threshold = 0.4  # Non-maximum suppression threshold
        self.max_detections = 10
        
        logger.info("Enhanced detection engine initialized")
    
    def load_model(self, model_path: str) -> None:
        """Load detection model with automatic fallback."""
        self.mobilenet_model_path = model_path
        
        # Try to load MobileNetV2 model first
        if self._load_mobilenet_model(model_path):
            self.primary_model_loaded = True
            self.current_model = "mobilenet"
            logger.info("Primary MobileNetV2 model loaded successfully")
        else:
            logger.warning("Failed to load MobileNetV2 model, falling back to OpenCV")
            self._load_fallback_model()
    
    def _load_mobilenet_model(self, model_path: str) -> bool:
        """Load MobileNetV2 TensorFlow Lite model."""
        if not TFLITE_AVAILABLE:
            logger.warning("TensorFlow Lite not available")
            return False
        
        try:
            if not os.path.exists(model_path):
                logger.error(f"Model file not found: {model_path}")
                return False
            
            # Load TensorFlow Lite model
            self.tflite_interpreter = tflite.Interpreter(model_path=model_path)
            self.tflite_interpreter.allocate_tensors()
            
            # Get input and output details
            self.input_details = self.tflite_interpreter.get_input_details()
            self.output_details = self.tflite_interpreter.get_output_details()
            
            # Validate model structure
            if not self._validate_model_structure():
                logger.error("Invalid model structure")
                return False
            
            # Check if model is quantized (INT8)
            self._check_quantization()
            
            logger.info(f"MobileNetV2 model loaded: {model_path}")
            logger.info(f"Input shape: {self.input_details[0]['shape']}")
            logger.info(f"Quantized: {self.quantized_model}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load MobileNetV2 model: {e}")
            return False
    
    def _load_fallback_model(self) -> None:
        """Load OpenCV Haar Cascade as fallback."""
        try:
            # Try to load a specific OpenCV model path if provided
            if self.opencv_model_path and os.path.exists(self.opencv_model_path):
                self.opencv_engine.load_model(self.opencv_model_path)
            else:
                # Use built-in cascade
                self.opencv_engine.load_model("")
            
            if self.opencv_engine.model_loaded:
                self.fallback_model_loaded = True
                self.current_model = "opencv"
                logger.info("OpenCV fallback model loaded successfully")
            else:
                logger.error("Failed to load fallback OpenCV model")
                
        except Exception as e:
            logger.error(f"Error loading fallback model: {e}")
    
    def _validate_model_structure(self) -> bool:
        """Validate that the loaded model has expected structure."""
        try:
            # Check input details
            if len(self.input_details) != 1:
                logger.error(f"Expected 1 input, got {len(self.input_details)}")
                return False
            
            input_shape = self.input_details[0]['shape']
            if len(input_shape) != 4:
                logger.error(f"Expected 4D input tensor, got shape {input_shape}")
                return False
            
            # Update input size based on model
            if input_shape[1] > 0 and input_shape[2] > 0:
                self.input_size = (input_shape[1], input_shape[2])
                logger.info(f"Model input size: {self.input_size}")
            
            # Check output details (expecting detection outputs)
            if len(self.output_details) < 3:
                logger.warning(f"Expected at least 3 outputs for object detection, got {len(self.output_details)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Model validation failed: {e}")
            return False
    
    def _check_quantization(self) -> None:
        """Check if the model is quantized (INT8)."""
        try:
            input_dtype = self.input_details[0]['dtype']
            if input_dtype == np.uint8:
                self.quantized_model = True
                logger.info("Model is quantized (INT8)")
            else:
                self.quantized_model = False
                logger.info(f"Model uses {input_dtype} precision")
                
        except Exception as e:
            logger.warning(f"Could not determine model quantization: {e}")
            self.quantized_model = False
    
    def detect_cats(self, frame: Any) -> List[Detection]:
        """Detect cats using the best available model."""
        if frame is None:
            return []
        
        # Try primary model first
        if self.primary_model_loaded and self.current_model == "mobilenet":
            try:
                detections = self._detect_with_mobilenet(frame)
                if detections:  # If we got valid detections
                    return detections
                else:
                    logger.debug("No detections from MobileNet, trying fallback")
            except Exception as e:
                logger.warning(f"MobileNet detection failed: {e}, falling back to OpenCV")
                self.current_model = "opencv"
        
        # Use fallback model
        if self.fallback_model_loaded and self.current_model == "opencv":
            try:
                return self.opencv_engine.detect_cats(frame)
            except Exception as e:
                logger.error(f"Fallback detection failed: {e}")
                return []
        
        logger.warning("No working detection model available")
        return []
    
    def _detect_with_mobilenet(self, frame: Any) -> List[Detection]:
        """Perform cat detection using MobileNetV2."""
        if not OPENCV_AVAILABLE or not TFLITE_AVAILABLE:
            return []
        
        try:
            # Preprocess frame for MobileNet
            input_tensor = self._preprocess_frame_for_mobilenet(frame)
            
            # Run inference
            self.tflite_interpreter.set_tensor(self.input_details[0]['index'], input_tensor)
            self.tflite_interpreter.invoke()
            
            # Get outputs
            outputs = self._get_model_outputs()
            
            # Post-process outputs to get detections
            detections = self._postprocess_mobilenet_outputs(outputs, frame.shape)
            
            # Filter for cats only and apply confidence threshold
            cat_detections = self._filter_cat_detections(detections)
            
            # Apply ROI filtering
            roi_detections = self._apply_roi_filtering(cat_detections)
            
            logger.debug(f"MobileNet detected {len(roi_detections)} cats")
            return roi_detections
            
        except Exception as e:
            logger.error(f"MobileNet detection error: {e}")
            raise
    
    def _preprocess_frame_for_mobilenet(self, frame: Any) -> np.ndarray:
        """Preprocess frame for MobileNetV2 input."""
        # Resize frame to model input size
        resized = cv2.resize(frame, self.input_size)
        
        # Convert BGR to RGB if needed
        if len(resized.shape) == 3 and resized.shape[2] == 3:
            rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        else:
            rgb_frame = resized
        
        # Normalize based on model quantization
        if self.quantized_model:
            # For quantized models, input is typically uint8 [0, 255]
            input_tensor = rgb_frame.astype(np.uint8)
        else:
            # For float models, normalize to [0, 1] or [-1, 1]
            input_tensor = rgb_frame.astype(np.float32) / 255.0
        
        # Add batch dimension
        input_tensor = np.expand_dims(input_tensor, axis=0)
        
        return input_tensor
    
    def _get_model_outputs(self) -> Dict[str, np.ndarray]:
        """Get all outputs from the model."""
        outputs = {}
        
        for i, output_detail in enumerate(self.output_details):
            output_data = self.tflite_interpreter.get_tensor(output_detail['index'])
            output_name = output_detail.get('name', f'output_{i}')
            outputs[output_name] = output_data
        
        return outputs
    
    def _postprocess_mobilenet_outputs(self, outputs: Dict[str, np.ndarray], 
                                     frame_shape: Tuple[int, ...]) -> List[Dict]:
        """Post-process MobileNet outputs to get bounding boxes and scores."""
        detections = []
        
        try:
            # Standard MobileNet SSD output format
            # outputs typically contain: boxes, classes, scores, num_detections
            
            # Try to identify output tensors
            boxes = None
            classes = None
            scores = None
            num_detections = None
            
            for name, data in outputs.items():
                shape = data.shape
                if len(shape) == 3 and shape[2] == 4:  # Bounding boxes [batch, num_boxes, 4]
                    boxes = data[0]  # Remove batch dimension
                elif len(shape) == 2 and shape[1] > 80:  # Classes (COCO has 80 classes)
                    classes = data[0]
                elif len(shape) == 2:  # Scores
                    scores = data[0]
                elif len(shape) == 1:  # Number of detections
                    num_detections = int(data[0])
            
            # If we couldn't identify outputs by shape, use order
            if boxes is None and len(outputs) >= 4:
                output_list = list(outputs.values())
                boxes = output_list[0][0] if len(output_list[0].shape) == 3 else None
                classes = output_list[1][0] if len(output_list[1].shape) == 2 else None
                scores = output_list[2][0] if len(output_list[2].shape) == 2 else None
                num_detections = int(output_list[3][0]) if len(output_list[3].shape) == 1 else 100
            
            if boxes is None or scores is None:
                logger.warning("Could not parse model outputs")
                return []
            
            # Convert normalized coordinates to pixel coordinates
            frame_h, frame_w = frame_shape[:2]
            
            # Process detections
            max_detections = min(len(boxes), num_detections if num_detections else len(boxes))
            
            for i in range(max_detections):
                score = float(scores[i]) if scores is not None else 0.5
                
                if score < self.confidence_threshold:
                    continue
                
                # Get bounding box (normalized coordinates)
                y1, x1, y2, x2 = boxes[i]
                
                # Convert to pixel coordinates
                x1_px = int(x1 * frame_w)
                y1_px = int(y1 * frame_h)
                x2_px = int(x2 * frame_w)
                y2_px = int(y2 * frame_h)
                
                # Calculate width and height
                width = x2_px - x1_px
                height = y2_px - y1_px
                
                # Skip invalid boxes
                if width <= 0 or height <= 0:
                    continue
                
                detection = {
                    'bbox': (x1_px, y1_px, width, height),
                    'confidence': score,
                    'class_id': int(classes[i]) if classes is not None else self.cat_class_id
                }
                
                detections.append(detection)
            
            # Apply non-maximum suppression
            detections = self._apply_nms(detections)
            
            return detections
            
        except Exception as e:
            logger.error(f"Error post-processing MobileNet outputs: {e}")
            return []
    
    def _apply_nms(self, detections: List[Dict]) -> List[Dict]:
        """Apply non-maximum suppression to remove overlapping detections."""
        if not detections or not OPENCV_AVAILABLE:
            return detections
        
        try:
            # Extract bounding boxes and scores
            boxes = []
            scores = []
            
            for det in detections:
                x, y, w, h = det['bbox']
                boxes.append([x, y, x + w, y + h])  # Convert to x1,y1,x2,y2 format
                scores.append(det['confidence'])
            
            # Apply NMS
            indices = cv2.dnn.NMSBoxes(boxes, scores, self.confidence_threshold, self.nms_threshold)
            
            # Filter detections based on NMS results
            if len(indices) > 0:
                indices = indices.flatten()
                return [detections[i] for i in indices]
            else:
                return []
                
        except Exception as e:
            logger.warning(f"NMS failed, returning all detections: {e}")
            return detections
    
    def _filter_cat_detections(self, detections: List[Dict]) -> List[Detection]:
        """Filter detections to only include cats."""
        cat_detections = []
        
        for det in detections:
            class_id = det.get('class_id', self.cat_class_id)
            
            # Check if detection is a cat (class_id 16 in COCO dataset)
            if class_id == self.cat_class_id:
                x, y, w, h = det['bbox']
                confidence = det['confidence']
                
                bbox = BoundingBox(
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                    confidence=confidence
                )
                
                detection = Detection(
                    timestamp=datetime.now(),
                    bounding_boxes=[bbox],
                    frame_width=640,  # Will be updated with actual frame size
                    frame_height=480,
                    raw_confidence=confidence
                )
                
                cat_detections.append(detection)
        
        return cat_detections
    
    def _apply_roi_filtering(self, detections: List[Detection]) -> List[Detection]:
        """Filter detections to only include those in the ROI."""
        if not detections:
            return detections
        
        roi_x, roi_y, roi_w, roi_h = self.roi
        filtered_detections = []
        
        for detection in detections:
            for bbox in detection.bounding_boxes:
                # Check if bounding box center is within ROI
                center_x = bbox.x + bbox.width // 2
                center_y = bbox.y + bbox.height // 2
                
                if (roi_x <= center_x <= roi_x + roi_w and 
                    roi_y <= center_y <= roi_y + roi_h):
                    filtered_detections.append(detection)
                    break  # Only need one bbox to be in ROI
        
        return filtered_detections
    
    def set_confidence_threshold(self, threshold: float) -> None:
        """Set detection confidence threshold."""
        self.confidence_threshold = max(0.0, min(1.0, threshold))
        
        # Also update OpenCV engine threshold
        if self.opencv_engine:
            self.opencv_engine.set_confidence_threshold(threshold)
        
        logger.info(f"Detection confidence threshold set to {self.confidence_threshold}")
    
    def set_roi(self, roi: Tuple[int, int, int, int]) -> None:
        """Set region of interest for detection."""
        self.roi = roi
        
        # Also update OpenCV engine ROI
        if self.opencv_engine:
            self.opencv_engine.set_roi(roi)
        
        logger.info(f"Detection ROI set to {roi}")
    
    def set_opencv_model_path(self, model_path: str) -> None:
        """Set OpenCV model path for fallback."""
        self.opencv_model_path = model_path
        if self.opencv_engine:
            self.opencv_engine.load_model(model_path)
    
    def get_current_model(self) -> str:
        """Get the currently active model."""
        return self.current_model
    
    def force_fallback_to_opencv(self) -> bool:
        """Force fallback to OpenCV model."""
        if self.fallback_model_loaded:
            self.current_model = "opencv"
            logger.info("Forced fallback to OpenCV model")
            return True
        else:
            logger.warning("OpenCV fallback model not available")
            return False
    
    def switch_to_mobilenet(self) -> bool:
        """Switch back to MobileNet model if available."""
        if self.primary_model_loaded:
            self.current_model = "mobilenet"
            logger.info("Switched to MobileNet model")
            return True
        else:
            logger.warning("MobileNet model not available")
            return False
    
    def optimize_for_raspberry_pi_zero_w(self) -> Dict[str, Any]:
        """Apply Raspberry Pi Zero W specific optimizations."""
        optimizations = []
        
        try:
            # 1. Optimize MobileNet input size for ARM
            self.input_size = (192, 192)  # Smaller input size for better performance
            optimizations.append("Reduced MobileNet input size to 192x192")
            
            # 2. Adjust detection parameters for ARM performance
            self.confidence_threshold = max(0.75, self.confidence_threshold)  # Higher threshold
            self.nms_threshold = 0.5  # More aggressive NMS
            self.max_detections = 5   # Fewer max detections
            optimizations.append("Optimized detection parameters for ARM")
            
            # 3. Enable ARM optimizations flag
            self.arm_optimized = True
            optimizations.append("ARM optimizations enabled")
            
            # 4. Optimize OpenCV fallback engine
            if self.opencv_engine:
                opencv_opts = self.opencv_engine.optimize_for_raspberry_pi_zero_w()
                if opencv_opts.get('success'):
                    optimizations.extend(opencv_opts.get('optimizations_applied', []))
            
            logger.info(f"Applied {len(optimizations)} Pi Zero W optimizations")
            
            return {
                "success": True,
                "optimizations_applied": optimizations,
                "current_model": self.current_model,
                "arm_optimized": self.arm_optimized,
                "input_size": self.input_size
            }
            
        except Exception as e:
            logger.error(f"Error applying Pi Zero W optimizations: {e}")
            return {
                "success": False,
                "error": str(e),
                "optimizations_applied": optimizations
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models."""
        info = {
            "primary_model_loaded": self.primary_model_loaded,
            "fallback_model_loaded": self.fallback_model_loaded,
            "current_model": self.current_model,
            "tflite_available": TFLITE_AVAILABLE,
            "opencv_available": OPENCV_AVAILABLE,
            "quantized_model": self.quantized_model,
            "arm_optimized": self.arm_optimized,
            "confidence_threshold": self.confidence_threshold,
            "roi": self.roi,
            "input_size": self.input_size
        }
        
        if self.tflite_interpreter:
            info["model_input_details"] = [
                {
                    "name": detail.get("name", f"input_{i}"),
                    "shape": detail["shape"].tolist(),
                    "dtype": str(detail["dtype"])
                }
                for i, detail in enumerate(self.input_details)
            ]
            
            info["model_output_details"] = [
                {
                    "name": detail.get("name", f"output_{i}"),
                    "shape": detail["shape"].tolist(),
                    "dtype": str(detail["dtype"])
                }
                for i, detail in enumerate(self.output_details)
            ]
        
        return info