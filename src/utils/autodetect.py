
import cv2
import numpy as np
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")

class AutoDetection:
    def __init__(self):
        # Paths to model files
        self.model_weights = os.path.join(
            os.path.dirname(__file__), "darknet/cfg/yolov4-tiny.weights"
        )
        self.model_cfg = os.path.join(
            os.path.dirname(__file__), "darknet/cfg/yolov4-tiny.cfg"
        )
        self.classes_file = os.path.join(os.path.dirname(__file__), "electronics.names")

        # Verify file paths
        if not os.path.exists(self.model_weights):
            raise FileNotFoundError(f"Model weights not found at {self.model_weights}")
        if not os.path.exists(self.model_cfg):
            raise FileNotFoundError(f"Model config not found at {self.model_cfg}")
        if not os.path.exists(self.classes_file):
            raise FileNotFoundError(f"Classes file not found at {self.classes_file}")

        # Load YOLO network
        self.net = cv2.dnn.readNet(self.model_weights, self.model_cfg)
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

        # Load class labels
        with open(self.classes_file, "r") as f:
            self.classes = f.read().strip().split("\n")

        logging.info("YOLO model loaded successfully.")

    def detect_objects(self, frame):
        """
        Detects objects in the given frame using YOLO.
        """
        height, width = frame.shape[:2]

        # Preprocess frame
        blob = cv2.dnn.blobFromImage(
            frame, 1 / 255.0, (416, 416), (0, 0, 0), swapRB=True, crop=False
        )
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

                # Filter detections
                if confidence > 0.5:
                    box = detection[:4] * np.array([width, height, width, height])
                    (center_x, center_y, w, h) = box.astype("int")

                    # Calculate coordinates
                    x = int(center_x - (w / 2))
                    y = int(center_y - (h / 2))
                    label = f"{self.classes[class_id]}: {confidence:.2f}"

                    objects.append({"bbox": (x, y, int(w), int(h)), "label": label})

        return objects

    def associate_signals_with_objects(self, objects, signals):
        """
        Associates detected objects with signals (e.g., Wi-Fi, Bluetooth).
        """
        associated_data = []

        for obj in objects:
            obj_x, obj_y, obj_w, obj_h = obj["bbox"]
            obj_center = (obj_x + obj_w // 2, obj_y + obj_h // 2)

            best_match = None
            best_distance = float("inf")

            for signal in signals:
                signal_position = signal.get("position")  # Triangulated position
                if signal_position:
                    distance = np.linalg.norm(
                        np.array(obj_center) - np.array(signal_position)
                    )
                    if distance < best_distance:
                        best_distance = distance
                        best_match = signal

            if best_match:
                associated_data.append({"object": obj, "signal": best_match})

        return associated_data

# Singleton instance
autodetect = AutoDetection()