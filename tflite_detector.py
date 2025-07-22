import cv2
import numpy as np
from tflite_runtime.interpreter import Interpreter

class TFLiteDetector:
    def __init__(self, model_path, label_map=None, score_threshold=0.5):
        # 1) Load INT8 TFLite model and allocate tensors
        self.interp = Interpreter(model_path)
        self.interp.allocate_tensors()

        # 2) Grab I/O details
        io = self.interp.get_input_details()[0]
        self.in_idx = io["index"]
        self.input_h = io["shape"][1]
        self.input_w = io["shape"][2]
        self.input_t = io["dtype"]
        self.scale, self.zero_point = io["quantization"]

        out_details = self.interp.get_output_details()
        self.out_idx = {
            "boxes": out_details[0]["index"],
            "classes": out_details[1]["index"],
            "scores": out_details[2]["index"],
            "count": out_details[3]["index"],
        }

        self.score_thresh = score_threshold
        self.labels = label_map or {}

    def detect(self, frame, motion_detected):
        if not motion_detected:
            return [], frame

        # Preprocess
        img = cv2.resize(frame, (self.input_w, self.input_h))
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        inp = (rgb / self.scale + self.zero_point).astype(self.input_t)[None, ...]

        # Run inference
        self.interp.set_tensor(self.in_idx, inp)
        self.interp.invoke()

        boxes = self.interp.get_tensor(self.out_idx["boxes"])[0]
        classes = self.interp.get_tensor(self.out_idx["classes"])[0]
        scores = self.interp.get_tensor(self.out_idx["scores"])[0]
        count = int(self.interp.get_tensor(self.out_idx["count"])[0])

        h, w, _ = frame.shape
        detections = []
        for i in range(count):
            if scores[i] < self.score_thresh:
                continue
            ymin, xmin, ymax, xmax = boxes[i]
            x1, y1 = int(xmin * w), int(ymin * h)
            x2, y2 = int(xmax * w), int(ymax * h)
            detections.append((x1, y1, x2 - x1, y2 - y1))

            label = self.labels.get(int(classes[i]), str(int(classes[i])))
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        return detections, frame
