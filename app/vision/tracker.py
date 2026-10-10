from ultralytics import YOLO


class PersonTracker:
    def __init__(self):
        self.model = YOLO("models/best.pt")

    def track(self, frame):
        results = self.model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            verbose=False
        )

        return results