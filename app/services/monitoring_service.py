
import cv2
import numpy as np

from app.vision.violation_engine import ViolationEngine
from app.services.evidence_service import EvidenceService
from app.services.incident_service import IncidentService


class MonitoringService:

    def __init__(
        self,
        model,
        restricted_zone,
        db,
        snapshot_dir="snapshots"
    ):
        self.model = model
        self.restricted_zone = restricted_zone
        self.db = db

        self.violation_engine = ViolationEngine(
            confidence_threshold=0.50,
            required_inside_frames=3
        )

        self.evidence_service = EvidenceService(
            snapshot_dir=snapshot_dir
        )

        # Minimum confidence for PPE detections.
        self.helmet_confidence_threshold = 0.30
        self.vest_confidence_threshold = 0.50
    def get_bottom_center(self, box):
        x1, y1, x2, y2 = box

        return (
            int((x1 + x2) / 2),
            int(y2)
        )

    def is_inside_zone(self, point):
        if not self.restricted_zone or len(self.restricted_zone) < 3:
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

    def get_ppe_status(self, person_box, ppe_detections):
        """
        Associate helmet and safety-vest detections with a person.

        Returns:
            status, detected_items
        """

        px1, py1, px2, py2 = person_box

        person_width = max(px2 - px1, 1)
        person_height = max(py2 - py1, 1)

        helmet_found = False
        vest_found = False

        for item in ppe_detections:
            class_name = item["class_name"]
            confidence = item["confidence"]

            if class_name == "helmet":
                if confidence <= self.helmet_confidence_threshold:
                    continue

            elif class_name in ("safety-vest", "safety_vest", "vest"):
                if confidence < self.vest_confidence_threshold:
                    continue

            x1, y1, x2, y2 = item["box"]

            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2

            # Allow a small horizontal margin around the person.
            within_person_width = (
                px1 - person_width * 0.10
                <= center_x
                <= px2 + person_width * 0.10
            )

            if not within_person_width:
                continue

            relative_y = (center_y - py1) / person_height

            # Helmet should be near the head/top of the person.
            if (
                class_name == "helmet"
                and -0.05 <= relative_y <= 0.40
            ):
                helmet_found = True

            # Safety vest should be around the upper torso.
            elif (
                class_name in ("safety-vest", "safety_vest", "vest")
                and 0.15 <= relative_y <= 0.80
            ):
                vest_found = True

        detected_items = []

        if helmet_found:
            detected_items.append("helmet")

        if vest_found:
            detected_items.append("safety-vest")

        # Both required items must be detected for a compliant result.
        if helmet_found and vest_found:
            return "with_ppe", detected_items

        return "without_ppe", detected_items

    def process_frame(self, frame):
        results = self.model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            verbose=False
        )

        result = results[0]
        annotated_frame = frame.copy()

        # Draw the restricted zone.
        if self.restricted_zone and len(self.restricted_zone) >= 3:
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

        if result.boxes is None or len(result.boxes) == 0:
            return annotated_frame

        boxes = result.boxes

        # First collect helmet and vest detections.
        # This lets us evaluate PPE before processing each person.
        ppe_detections = []

        for i in range(len(boxes)):
            class_id = int(boxes.cls[i].item())
            class_name = str(
                self.model.names[class_id]
            ).strip().lower().replace("_", "-")

            if class_name not in (
                "helmet",
                "safety-vest",
                "vest"
            ):
                continue

            ppe_detections.append({
                "class_name": class_name,
                "confidence": float(boxes.conf[i].item()),
                "box": tuple(
                    map(int, boxes.xyxy[i].tolist())
                )
            })

        # Process tracked people.
        for i in range(len(boxes)):
            class_id = int(boxes.cls[i].item())

            class_name = str(
                self.model.names[class_id]
            ).strip().lower()

            if class_name != "person":
                continue

            confidence = float(boxes.conf[i].item())

            # Preserve the existing tracking requirement.
            if boxes.id is None or boxes.id[i] is None:
                continue

            track_id = int(boxes.id[i].item())

            x1, y1, x2, y2 = map(
                int,
                boxes.xyxy[i].tolist()
            )

            person_box = (x1, y1, x2, y2)

            person_point = self.get_bottom_center(
                person_box
            )

            inside_zone = self.is_inside_zone(person_point)

            ppe_status, detected_items = self.get_ppe_status(
                person_box,
                ppe_detections
            )

            # Existing engine confirms entry after 3 frames
            # and prevents repeat incidents while inside.
            violation = self.violation_engine.check_restricted_zone(
                track_id=track_id,
                confidence=confidence,
                inside_zone=inside_zone
            )

            # Green for detected PPE compliance, red otherwise.
            if ppe_status == "with_ppe":
                person_color = (0, 180, 0)
                status_text = "PPE OK"
            else:
                person_color = (0, 0, 255)
                status_text = "PPE MISSING"

            if not inside_zone:
                person_color = (255, 180, 0)

            cv2.rectangle(
                annotated_frame,
                (x1, y1),
                (x2, y2),
                person_color,
                2
            )

            cv2.putText(
                annotated_frame,
                f"ID: {track_id} | {status_text}",
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                person_color,
                2
            )

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

            # Create an incident only after zone entry is confirmed.
            
            if violation:
                
                if ppe_status == "with_ppe":
                    violation_type = "restricted_zone_entry_with_ppe"
                    message = "Person entered with PPE kit"

                elif detected_items:
                    missing_items = []

                    if "helmet" not in detected_items:
                        missing_items.append("Helmet")

                    if "safety-vest" not in detected_items:
                        missing_items.append("Safety Vest")

                    violation_type = "restricted_zone_entry_partial_ppe"

                    message = (
                        "Person entered with incomplete PPE. Missing: "
                        + " and ".join(missing_items)
                    )

                else:
                    violation_type = "restricted_zone_entry_without_ppe"
                    message = "Person entered without PPE kit"
                    missing_items = ["Helmet", "Safety Vest"]

                violation["violation_type"] = violation_type
                violation["ppe_status"] = ppe_status
                violation["detected_ppe"] = detected_items
                violation["message"] = message

                print("\n" + "=" * 50)
                print(f"PERSON ID: {track_id}")
                print(f"EVENT: {message}")
                print(f"PPE DETECTED: {detected_items}")
                print(f"PERSON CONFIDENCE: {confidence:.2f}")
                print("=" * 50)

                evidence = self.evidence_service.save_violation_evidence(
                    original_frame=frame,
                    annotated_frame=annotated_frame,
                    violation=violation
                )

                if evidence:
                    incident = IncidentService.create_incident(
                        db=self.db,
                        violation_type=violation_type,
                        person_track_id=track_id,
                        confidence=confidence,
                        snapshot_path=evidence["original_path"],
                        annotated_snapshot_path=evidence["annotated_path"],
                        message=message
                    )

                    print(f"Incident saved: {incident.id}")


        return annotated_frame
