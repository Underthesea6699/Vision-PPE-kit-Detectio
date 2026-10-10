
import time

import cv2
from ultralytics import YOLO

from app.database.database import SessionLocal
from app.services.monitoring_service import MonitoringService
from app.services.zone_service import ZoneService


# Shared status for the dashboard's polling endpoint.
STREAM_STATUS = {
    "local": {
        "status": "idle",
        "message": "Local video has not started."
    },
    "phone": {
        "status": "idle",
        "message": "Phone camera has not started."
    }
}

<<<<<<< Updated upstream
    def __init__(
        self,
        video_source,
        model_path="yolov8n.pt"
    ):
        self.zone_service = ZoneService()
=======

class VideoStreamService:
    def __init__(
        self,
        video_source,
        model_path="models/best.pt",
        reconnect_delay=2,
        max_reconnect_attempts=5,
    ):
        self.zone_service = ZoneService()
>>>>>>> Stashed changes
        self.video_source = video_source
        self.model_path = model_path
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts

        self.zone_service = ZoneService()
        self.model = YOLO(model_path)

        self.source_key = (
            "phone"
            if isinstance(video_source, str)
            and video_source.lower().startswith("rtsp://")
            else "local"
        )

    def _set_status(self, status, message):
        STREAM_STATUS[self.source_key] = {
            "status": status,
            "message": message,
            "updated_at": time.time(),
        }
        print(f"[{self.source_key}] {status}: {message}")

    def _open_capture(self):
        if (
            isinstance(self.video_source, str)
            and self.video_source.lower().startswith("rtsp://")
        ):
            cap = cv2.VideoCapture(
                self.video_source,
                cv2.CAP_FFMPEG
            )
        else:
            cap = cv2.VideoCapture(self.video_source)

        return cap

    def generate_frames(self):
        restricted_zone = self.zone_service.get_zone()
        db = None
        cap = None
        reconnect_attempts = 0
        is_rtsp = self.source_key == "phone"

        try:
            db = SessionLocal()

            monitoring_service = MonitoringService(
                model=self.model,
                restricted_zone=restricted_zone,
                db=db,
            )

            while True:
                self._set_status(
                    "connecting",
                    "Connecting to video source."
                )

                cap = self._open_capture()

                if not cap.isOpened():
                    cap.release()
                    cap = None
                    reconnect_attempts += 1

                    if reconnect_attempts >= self.max_reconnect_attempts:
                        self._set_status(
                            "disconnected",
                            "Could not connect after multiple attempts."
                        )
                        break

                    self._set_status(
                        "reconnecting",
                        f"Retry {reconnect_attempts}/"
                        f"{self.max_reconnect_attempts} in "
                        f"{self.reconnect_delay} seconds."
                    )
                    time.sleep(self.reconnect_delay)
                    continue

                while True:
                    success, frame = cap.read()

                    if not success:
                        if not is_rtsp:
                            self._set_status(
                                "ended",
                                "Local video playback has ended."
                            )
                            return

                        break


                    reconnect_attempts = 0

                    # Update status only when the connection state changes.
                    if STREAM_STATUS[self.source_key]["status"] != "connected":
                        self._set_status(
                            "connected",
                            "Receiving live video frames."
                        )

                    annotated_frame = monitoring_service.process_frame(frame)

                    encoded, buffer = cv2.imencode(
                        ".jpg",
                        annotated_frame
                    )

                    if encoded:
                        yield (
                            b"--frame\r\n"
                            b"Content-Type: image/jpeg\r\n\r\n"
                            + buffer.tobytes()
                            + b"\r\n"
                        )

                if cap is not None:
                    cap.release()
                    cap = None

                reconnect_attempts += 1

                if reconnect_attempts >= self.max_reconnect_attempts:
                    self._set_status(
                        "disconnected",
                        "Camera feed lost. Maximum retries reached."
                    )
                    break

                self._set_status(
                    "reconnecting",
                    f"Camera feed lost. Retry {reconnect_attempts}/"
                    f"{self.max_reconnect_attempts} in "
                    f"{self.reconnect_delay} seconds."
                )
                time.sleep(self.reconnect_delay)

        except Exception as error:
            self._set_status(
                "error",
                f"Video processing failed: {error}"
            )
            raise

        finally:
            if cap is not None:
                cap.release()

            if db is not None:
                db.close()

            # Preserve "ended", "disconnected", or "error" state.
            current = STREAM_STATUS[self.source_key]["status"]
            if current not in ("ended", "disconnected", "error"):
                self._set_status(
                    "disconnected",
                    "Video stream stopped."
                )

            print("Video stream resources released.")
