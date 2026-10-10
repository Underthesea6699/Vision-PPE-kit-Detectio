from ultralytics import YOLO


class ObjectDetector:
    def __init__(self):
        self.model = YOLO("yolov8n.pt")

    def detect(self, image):
        results = self.model(image)
        return results