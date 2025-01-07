# src/autodetect.py

import cv2
from ultralytics import YOLO
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

# Load YOLO model
model = YOLO('yolov5n.pt')  # Lightweight model for Raspberry Pi

class AutoDetection:
    def __init__(self):
        self.detected_objects = []  # Store detected objects with bounding boxes and labels

    def detect_objects(self, frame):
        """
        Detects objects in the given frame using YOLO.
        """
        results = model(frame)
        objects = []
        for detection in results.xyxy[0]:  # x1, y1, x2, y2, conf, class
            x1, y1, x2, y2, conf, cls = detection.tolist()
            label = f"{model.names[int(cls)]} {conf:.2f}"
            objects.append({"bbox": (int(x1), int(y1), int(x2), int(y2)), "label": label})
        self.detected_objects = objects
        return objects

    def get_detected_objects(self):
        """
        Returns the currently detected objects.
        """
        return self.detected_objects


# Singleton instance
autodetect = AutoDetection()
