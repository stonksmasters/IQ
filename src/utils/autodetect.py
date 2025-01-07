import cv2
import numpy as np
import os
import logging
from utils.autodetect import autodetect

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

class AutoDetection:
    def __init__(self):
        # Paths to model files
        self.model_weights = os.path.join(os.path.dirname(__file__), "yolov4-tiny.weights")  # Pretrained YOLO weights
        self.model_cfg = os.path.join(os.path.dirname(__file__), "yolov4-tiny.cfg")  # YOLO configuration file
        self.classes_file = os.path.join(os.path.dirname(__file__), "electronics.names")  # Custom classes file

        # Ensure all files exist
        for file_path in [self.model_weights, self.model_cfg, self.classes_file]:
            if not os.path.exists(file_path):
                logging.error(f"File not found: {file_path}")
                raise FileNotFoundError(f"Required file missing: {file_path}")

        # Load YOLO network
        self.net = cv2.dnn.readNet(self.model_weights, self.model_cfg)
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

        # Load class labels
        with open(self.classes_file, "r") as f:
            self.classes = f.read().strip().split("\n")

        logging.info("YOLO model loaded successfully with the following classes:")
        logging.info(self.classes)

    def detect_objects(self, frame):
        """
        Detects objects in the given frame using YOLO.

        Args:
            frame (numpy.ndarray): The input video frame.

        Returns:
            list: Detected objects with their bounding boxes and labels.
        """
        height, width = frame.shape[:2]

        # Preprocess frame
        blob = cv2.dnn.blobFromImage(frame, 1 / 255.0, (416, 416), (0, 0, 0), swapRB=True, crop=False)
        self.net.setInput(blob)

        # Perform forward pass
        layer_names = self.net.getUnconnectedOutLayersNames()
        outputs = self.net.forward(layer_names)

        objects = []
        for output in outputs:
            for detection in output:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]

                # Filter detections based on confidence threshold
                if confidence > 0.5:
                    box = detection[:4] * np.array([width, height, width, height])
                    (center_x, center_y, w, h) = box.astype("int")

                    # Calculate coordinates
                    x = int(center_x - (w / 2))
                    y = int(center_y - (h / 2))
                    label = f"{self.classes[class_id]}: {confidence:.2f}"

                    objects.append({"bbox": (x, y, int(w), int(h)), "label": label})

        logging.info(f"Detected objects: {objects}")
        return objects


# Singleton instance
autodetect = AutoDetection()
