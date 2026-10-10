import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from app.services.evidence_service import EvidenceService


class EvidenceOverlayTests(unittest.TestCase):

    def test_saved_annotated_snapshot_contains_incident_message(self):
        saved_images = {}

        def capture_image(path, image):
            saved_images[path] = image.copy()
            return True

        frame = np.zeros((240, 640, 3), dtype=np.uint8)
        annotated_frame = frame.copy()

        with tempfile.TemporaryDirectory() as directory:
            service = EvidenceService(snapshot_dir=directory)
            with patch(
                "app.services.evidence_service.cv2.imwrite",
                side_effect=capture_image
            ), patch(
                "app.services.evidence_service.cv2.putText",
                wraps=cv2.putText
            ) as put_text, patch("builtins.print"):
                result = service.save_violation_evidence(
                    original_frame=frame,
                    annotated_frame=annotated_frame,
                    violation={
                        "track_id": 7,
                        "violation_type": "restricted_zone_entry",
                        "message": "Person entered without PPE kit"
                    }
                )

        saved_annotated = saved_images[result["annotated_path"]]
        self.assertTrue(np.any(saved_annotated != annotated_frame))
        self.assertTrue(np.all(annotated_frame == 0))
        self.assertTrue(np.any(saved_annotated[:60] != 0))
        self.assertTrue(any(
            call.args[1] == "Person entered without PPE kit"
            for call in put_text.call_args_list
        ))
