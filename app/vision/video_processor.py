import cv2
import numpy as np
from datetime import datetime
from pathlib import Path

from ultralytics import YOLO

from app.vision.violation_engine import ViolationEngine
from app.services.evidence_service import EvidenceService
from app.services.incident_service import IncidentService
from app.database.database import SessionLocal


class VideoProcessor:

    def __init__(
        self,
        video_source,
        model_path="models/best.pt",
        restricted_zone=None,
        snapshot_dir="snapshots"
    ):
        self.video_source = video_source
        self.model = YOLO(model_path)

        self.restricted_zone = restricted_zone

        self.violation_engine = ViolationEngine(
            confidence_threshold=0.50,
            required_inside_frames=3
        )

        self.evidence_service = EvidenceService(
            snapshot_dir=snapshot_dir
        )

    def get_bottom_center(self, box):
        x1, y1, x2, y2 = box

        center_x = int((x1 + x2) / 2)
        bottom_y = int(y2)

        return center_x, bottom_y

    def is_inside_zone(self, point):
        if self.restricted_zone is None:
            return False

        contour = np.array(
            self.restricted_zone,
            dtype=np.int32
        )

        result = cv2.pointPolygonTest(
            contour,
            (float(point[0]), float(point[1])),
            False
        )

        return result >= 0

    def process(self):

        cap = cv2.VideoCapture(self.video_source)

        if not cap.isOpened():
            print(
                f"❌ Could not open video: "
                f"{self.video_source}"
            )
            return

        print("Video processing started...")
        print("Press Q to stop.")

        db = SessionLocal()

        try:

            while True:

                success, frame = cap.read()

                if not success:
                    print("Video finished.")
                    break

                results = self.model.track(
                    frame,
                    persist=True,
                    tracker="bytetrack.yaml",
                    verbose=False
                )

                result = results[0]

                annotated_frame = frame.copy()

                # Draw restricted zone
                if self.restricted_zone:

                    polygon = np.array(
                        self.restricted_zone,
                        dtype=np.int32
                    )

                    cv2.polylines(
                        annotated_frame,
                        [polygon],
                        True,
                        (255, 0, 0),
                        2
                    )

                if result.boxes is not None:

                    boxes = result.boxes

                    for i in range(len(boxes)):

                        cls_id = int(
                            boxes.cls[i].item()
                        )

                        class_name = self.model.names[
                            cls_id
                        ]

                        # Only persons matter
                        if class_name != "person":
                            continue

                        confidence = float(
                            boxes.conf[i].item()
                        )

                        # Tracking ID
                        if boxes.id is None:
                            continue

                        track_id = int(
                            boxes.id[i].item()
                        )

                        # Bounding box
                        x1, y1, x2, y2 = map(
                            int,
                            boxes.xyxy[i].tolist()
                        )

                        person_point = (
                            (x1 + x2) // 2,
                            y2
                        )

                        # Check restricted zone
                        inside_zone = self.is_inside_zone(
                            person_point
                        )

                        # Check violation
                        violation = (
                            self.violation_engine
                            .check_restricted_zone(
                                track_id=track_id,
                                confidence=confidence,
                                inside_zone=inside_zone
                            )
                        )

                        # Draw bounding box
                        cv2.rectangle(
                            annotated_frame,
                            (x1, y1),
                            (x2, y2),
                            (255, 0, 0),
                            2
                        )

                        # Draw ID
                        cv2.putText(
                            annotated_frame,
                            f"ID: {track_id}",
                            (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (255, 0, 0),
                            2
                        )

                        # Draw bottom-center point
                        point_color = (
                            (0, 0, 255)
                            if inside_zone
                            else (0, 255, 0)
                        )

                        cv2.circle(
                            annotated_frame,
                            person_point,
                            6,
                            point_color,
                            -1
                        )

                        # --------------------------------
                        # CONFIRMED VIOLATION
                        # --------------------------------

                        if violation:
                            violation["message"] = (
                                "Person entered restricted zone"
                            )

                            print(
                                "\n🚨 "
                                "RESTRICTED-ZONE "
                                "VIOLATION CONFIRMED!"
                            )

                            print(
                                f"Person ID: "
                                f"{track_id}"
                            )

                            print(
                                f"Confidence: "
                                f"{confidence:.2f}"
                            )

                            print(
                                f"Inside frames: "
                                f"{violation['inside_frames']}"
                            )

                            # Save evidence
                            evidence = (
                                self.evidence_service
                                .save_violation_evidence(
                                    original_frame=frame,
                                    annotated_frame=
                                        annotated_frame,
                                    violation=violation
                                )
                            )

                            if evidence:

                                # Save incident
                                incident = (
                                    IncidentService
                                    .create_incident(
                                        db=db,
                                        violation_type=
                                            violation[
                                                "violation_type"
                                            ],
                                        person_track_id=
                                            track_id,
                                        confidence=
                                            confidence,
                                        snapshot_path=
                                            evidence[
                                                "original_path"
                                            ],
                                        annotated_snapshot_path=
                                            evidence[
                                                "annotated_path"
                                            ],
                                        message=violation["message"]
                                    )
                                )

                                print(
                                    "\n💾 Incident saved "
                                    "to Supabase!"
                                )

                                print(
                                    f"Incident ID: "
                                    f"{incident.id}"
                                )

                cv2.imshow(
                    "Vision-AI Monitoring System",
                    annotated_frame
                )

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

        finally:

            db.close()
            cap.release()
            cv2.destroyAllWindows()

            print(
                "\nVideo processing completed."
            )