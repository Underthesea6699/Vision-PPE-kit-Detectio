from datetime import datetime
from pathlib import Path

import cv2


class EvidenceService:
    """
    Handles saving evidence images for confirmed violations.
    """

    def __init__(self, snapshot_dir="snapshots"):
        self.snapshot_dir = Path(snapshot_dir)

        # Create the snapshot directory if it does not exist
        self.snapshot_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    def save_violation_evidence(
        self,
        original_frame,
        annotated_frame,
        violation
    ):
        """
        Save both original and annotated images
        for a confirmed violation.
        """

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        person_id = violation["track_id"]

        base_name = (
            f"restricted_zone_"
            f"person_{person_id}_"
            f"{timestamp}"
        )

        original_path = (
            self.snapshot_dir /
            f"{base_name}_original.jpg"
        )

        annotated_path = (
            self.snapshot_dir /
            f"{base_name}_annotated.jpg"
        )

        incident_message = (
            violation.get("message")
            or violation.get("violation_type", "Incident")
                .replace("_", " ")
                .title()
        )
        annotated_snapshot = annotated_frame.copy()
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.65
        thickness = 2
        margin = 12
        max_text_width = max(1, annotated_snapshot.shape[1] - margin * 2)
        lines = []
        current_line = ""

        for word in incident_message.split():
            candidate = f"{current_line} {word}".strip()
            text_width = cv2.getTextSize(
                candidate, font, font_scale, thickness
            )[0][0]

            if current_line and text_width > max_text_width:
                lines.append(current_line)
                current_line = word
            else:
                current_line = candidate

        if current_line:
            lines.append(current_line)

        line_height = cv2.getTextSize("Ag", font, font_scale, thickness)[0][1] + 10
        banner_height = min(
            annotated_snapshot.shape[0],
            margin * 2 + line_height * len(lines)
        )
        cv2.rectangle(
            annotated_snapshot,
            (0, 0),
            (annotated_snapshot.shape[1], banner_height),
            (0, 0, 0),
            -1
        )

        for index, line in enumerate(lines):
            baseline_y = margin + (index + 1) * line_height - 5
            if baseline_y > banner_height:
                break
            cv2.putText(
                annotated_snapshot,
                line,
                (margin, baseline_y),
                font,
                font_scale,
                (255, 255, 255),
                thickness,
                cv2.LINE_AA
            )

        # Save original frame
        original_saved = cv2.imwrite(
            str(original_path),
            original_frame
        )

        # Save annotated frame
        annotated_saved = cv2.imwrite(
            str(annotated_path),
            annotated_snapshot
        )

        if original_saved and annotated_saved:

            print("\n📸 Evidence saved!")

            print(
                f"Original: {original_path}"
            )

            print(
                f"Annotated: {annotated_path}"
            )

            return {
                "original_path": str(original_path),
                "annotated_path": str(annotated_path)
            }

        print("\n❌ Failed to save evidence.")

        return None