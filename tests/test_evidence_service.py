import cv2

from app.services.evidence_service import EvidenceService


# --------------------------------------------------
# Load test image
# --------------------------------------------------

image_path = "test_images/test.jpg"

frame = cv2.imread(image_path)

if frame is None:
    print(f"Could not load image: {image_path}")
    exit()


# --------------------------------------------------
# Create service
# --------------------------------------------------

evidence_service = EvidenceService(
    snapshot_dir="snapshots"
)


# --------------------------------------------------
# Fake violation for testing
# --------------------------------------------------

violation = {
    "violation_type": "restricted_zone_entry",
    "track_id": 10,
    "confidence": 0.85,
    "inside_frames": 3
}


# --------------------------------------------------
# Create annotated copy
# --------------------------------------------------

annotated_frame = frame.copy()

cv2.putText(
    annotated_frame,
    "RESTRICTED ZONE VIOLATION",
    (50, 50),
    cv2.FONT_HERSHEY_SIMPLEX,
    1,
    (0, 0, 255),
    2
)


# --------------------------------------------------
# Save evidence
# --------------------------------------------------

result = evidence_service.save_violation_evidence(
    original_frame=frame,
    annotated_frame=annotated_frame,
    violation=violation
)


print("\nEvidence service test completed.")

if result:
    print("\nSaved files:")
    print(result)