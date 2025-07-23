"""
TensorFlow Lite cat detector using INT8 quantized SSDLite MobileNet V2.
Optimized for maximum efficiency on Raspberry Pi Zero 2 W.
"""

import cv2
import numpy as np
import logging
import os
import time
from tflite_runtime.interpreter import Interpreter

try:
    from . import config
except ImportError:
    import config

logger = logging.getLogger(__name__)

class TFLiteDetector:
    """TensorFlow Lite cat detector using INT8 quantized model.
    Optimized for maximum efficiency on Pi Zero 2 W."""
    
    def __init__(self, model_path, label_map=None, score_threshold=None):
        """Initialize the TFLite detector.
        
        Args:
            model_path: Path to the TFLite model file
            label_map: Dictionary mapping class IDs to labels
            score_threshold: Detection confidence threshold (uses config if None)
        """
        # Use config values if not provided
        if score_threshold is None:
            score_threshold = config.CONFIDENCE_THRESHOLD
        
        self.score_thresh = score_threshold
        # COCO dataset labels (cat is class 16)
        self.labels = label_map or {
            0: "background", 1: "person", 2: "bicycle", 3: "car", 4: "motorcycle", 5: "airplane",
            6: "bus", 7: "train", 8: "truck", 9: "boat", 10: "traffic light", 11: "fire hydrant",
            12: "stop sign", 13: "parking meter", 14: "bench", 15: "bird", 16: "cat", 17: "dog",
            18: "horse", 19: "sheep", 20: "cow", 21: "elephant", 22: "bear", 23: "zebra",
            24: "giraffe", 25: "backpack", 26: "umbrella", 27: "handbag", 28: "tie", 29: "suitcase"
        }
        self.last_detection_time = 0
        self.detection_interval = config.DETECTION_INTERVAL
        
        # Validate model file exists
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        logger.info(f"Loading TFLite model from: {model_path}")
        
        try:
            # Load INT8 TFLite model and allocate tensors
            self.interp = Interpreter(model_path)
            self.interp.allocate_tensors()
            
            # Get input details
            io = self.interp.get_input_details()[0]
            self.in_idx = io["index"]
            self.input_h = io["shape"][1]
            self.input_w = io["shape"][2]
            self.input_t = io["dtype"]
            
            # Handle quantization parameters
            if "quantization" in io:
                self.scale, self.zero_point = io["quantization"]
                logger.info(f"Model uses quantization: scale={self.scale}, zero_point={self.zero_point}")
            else:
                self.scale, self.zero_point = 1.0, 0
                logger.info("Model does not use quantization")
            
            # Get output details
            out_details = self.interp.get_output_details()
            self.out_idx = {
                "boxes": out_details[0]["index"],
                "classes": out_details[1]["index"],
                "scores": out_details[2]["index"],
                "count": out_details[3]["index"],
            }
            
            logger.info(f"Model loaded successfully. Input shape: {self.input_h}x{self.input_w}")
            logger.info(f"Score threshold: {self.score_thresh}")
            
        except Exception as e:
            logger.error(f"Failed to load TFLite model: {e}")
            raise
    
    def detect(self, frame, motion_detected=False):
        """
        Detect cats in the frame (only when motion is detected).
        
        Args:
            frame: BGR image as numpy array
            motion_detected: Whether motion was detected in this frame
            
        Returns:
            (detections, annotated_frame) where:
                - detections is a list of (x, y, w, h) tuples
                - annotated_frame is the input frame with detection boxes drawn
        """
        # Skip detection if no motion detected (efficiency optimization)
        if not motion_detected:
            return [], frame
        
        # Skip detection if it's too soon since the last one
        current_time = time.time()
        if current_time - self.last_detection_time < self.detection_interval:
            return [], frame
        
        self.last_detection_time = current_time
        
        try:
            # Preprocess image
            img = cv2.resize(frame, (self.input_w, self.input_h))
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Apply quantization if needed
            if self.scale != 1.0 or self.zero_point != 0:
                inp = (rgb / self.scale + self.zero_point).astype(self.input_t)
            else:
                inp = rgb.astype(self.input_t)
            
            # Add batch dimension
            inp = inp[None, ...]
            
            # Run inference
            self.interp.set_tensor(self.in_idx, inp)
            self.interp.invoke()
            
            # Get detection results
            boxes = self.interp.get_tensor(self.out_idx["boxes"])[0]
            classes = self.interp.get_tensor(self.out_idx["classes"])[0]
            scores = self.interp.get_tensor(self.out_idx["scores"])[0]
            count = int(self.interp.get_tensor(self.out_idx["count"])[0])
            
            # Process detections
            h, w, _ = frame.shape
            detections = []
            annotated_frame = frame.copy()
            
            for i in range(count):
                if scores[i] < self.score_thresh:
                    continue
                
                # Convert normalized coordinates to pixel coordinates
                ymin, xmin, ymax, xmax = boxes[i]
                x1, y1 = int(xmin * w), int(ymin * h)
                x2, y2 = int(xmax * w), int(ymax * h)
                
                # Ensure coordinates are within frame bounds
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                
                detections.append((x1, y1, x2 - x1, y2 - y1))
                
                # Draw detection box and label
                label = self.labels.get(int(classes[i]), str(int(classes[i])))
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(annotated_frame, f'{label} {scores[i]:.2f}', 
                           (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            # Add detection count and motion status
            cv2.putText(annotated_frame, f'Cats: {len(detections)}', (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(annotated_frame, f'Motion: {"Yes" if motion_detected else "No"}', (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            
            return detections, annotated_frame
            
        except Exception as e:
            logger.error(f"Error during detection: {e}")
            return [], frame
