import cv2
import numpy as np
from datetime import datetime
from pathlib import Path
from ultralytics import YOLO


# --------------------------------------------------
# Configuration
# --------------------------------------------------

MODEL_PATH = "models/best.pt"
VIDEO_PATH = "test_videos/test.mp4"
SNAPSHOT_DIR = Path("snapshots")

RESTRICTED_ZONE = [
    (118, 963),
    (129, 404),
    (505, 413),
    (490, 950)
]


# --------------------------------------------------
# Setup
# --------------------------------------------------

model = YOLO(MODEL_PATH)

cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():
    print(f"Could not open video: {VIDEO_PATH}")
    exit()


# Create snapshots folder if it does not exist
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


# Store previous zone state of each tracked person
previous_states = {}


# Convert polygon to NumPy contour for OpenCV
contour = np.array(RESTRICTED_ZONE, dtype=np.int32)


# --------------------------------------------------
# Helper Functions
# --------------------------------------------------

def get_bottom_center(box):
    """
    Calculate the bottom-center point of a bounding box.

    Box format:
    x1, y1, x2, y2
    """

    x1, y1, x2, y2 = box

    center_x = int((x1 + x2) / 2)
    bottom_y = int(y2)

    return center_x, bottom_y


def is_inside_zone(point):
    """
    Check whether a point is inside the restricted zone.
    """

    result = cv2.pointPolygonTest(
        contour,
        (float(point[0]), float(point[1])),
        False
    )

    return result >= 0


def save_evidence(frame, person_id, confidence, position):
    """
    Save the current frame as evidence of a violation.
    """

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    filename = (
        f"restricted_zone_"
        f"person_{person_id}_"
        f"{timestamp}.jpg"
    )

    snapshot_path = SNAPSHOT_DIR / filename

    success = cv2.imwrite(str(snapshot_path), frame)

    if success:
        print("\n📸 Evidence snapshot saved!")
        print(f"File: {snapshot_path}")
        print(f"Person ID: {person_id}")
        print(f"Confidence: {confidence:.2f}")
        print(f"Position: {position}")
    else:
        print("\n❌ Failed to save evidence snapshot.")


# --------------------------------------------------
# Video Processing
# --------------------------------------------------

while True:

    success, frame = cap.read()

    if not success:
        print("Video finished or frame could not be read.")
        break


    # --------------------------------------------------
    # YOLO Tracking
    # --------------------------------------------------

    results = model.track(
        frame,
        persist=True,
        tracker="bytetrack.yaml",
        verbose=False
    )


    result = results[0]


    # --------------------------------------------------
    # Draw Restricted Zone
    # --------------------------------------------------

    cv2.polylines(
        frame,
        [contour],
        isClosed=True,
        color=(255, 0, 0),
        thickness=3
    )


    # --------------------------------------------------
    # Process Detected Objects
    # --------------------------------------------------

    if result.boxes.id is not None:

        boxes = result.boxes.xyxy.cpu().numpy()
        track_ids = result.boxes.id.cpu().numpy()
        class_ids = result.boxes.cls.cpu().numpy()
        confidences = result.boxes.conf.cpu().numpy()


        for box, track_id, class_id, confidence in zip(
            boxes,
            track_ids,
            class_ids,
            confidences
        ):

            class_name = model.names[int(class_id)]

            # We only care about people
            if class_name != "person":
                continue


            track_id = int(track_id)


            # --------------------------------------------------
            # Bounding Box
            # --------------------------------------------------

            x1, y1, x2, y2 = map(int, box)


            # --------------------------------------------------
            # Bottom Center
            # --------------------------------------------------

            person_point = get_bottom_center(
                (x1, y1, x2, y2)
            )


            # --------------------------------------------------
            # Zone Check
            # --------------------------------------------------

            current_inside = is_inside_zone(person_point)

            previous_inside = previous_states.get(
                track_id,
                False
            )


            # --------------------------------------------------
            # Draw Person Point
            # --------------------------------------------------

            if current_inside:

                # Red = inside restricted zone
                cv2.circle(
                    frame,
                    person_point,
                    6,
                    (0, 0, 255),
                    -1
                )

            else:

                # Green = outside restricted zone
                cv2.circle(
                    frame,
                    person_point,
                    6,
                    (0, 255, 0),
                    -1
                )


            # --------------------------------------------------
            # Restricted-Zone Entry
            # --------------------------------------------------

            if current_inside and not previous_inside:

                print("\n🚨 RESTRICTED-ZONE ENTRY!")

                print(f"Person ID: {track_id}")
                print(f"Confidence: {confidence:.2f}")
                print(f"Position: {person_point}")


                # Save evidence
                save_evidence(
                    frame,
                    track_id,
                    confidence,
                    person_point
                )


            # Update person's previous state
            previous_states[track_id] = current_inside


    # --------------------------------------------------
    # Display
    # --------------------------------------------------

    cv2.imshow(
        "Vision-AI Restricted Zone",
        frame
    )


    # Press Q to stop
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


# --------------------------------------------------
# Cleanup
# --------------------------------------------------

cap.release()
cv2.destroyAllWindows()

print("\nRestricted-zone test completed.")