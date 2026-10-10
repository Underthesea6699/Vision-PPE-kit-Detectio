
import cv2
from pathlib import Path

input_path = Path("runs/tracking/tracked_test/test.avi")
output_path = Path("runs/tracking/tracked_test/tracked_test.mp4")

cap = cv2.VideoCapture(str(input_path))

if not cap.isOpened():
    raise RuntimeError(f"Cannot open video: {input_path}")

fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer = cv2.VideoWriter(
    str(output_path), fourcc, fps, (width, height)
)

if not writer.isOpened():
    cap.release()
    raise RuntimeError("Could not create MP4 output")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    writer.write(frame)

cap.release()
writer.release()

print(f"MP4 saved to: {output_path.resolve()}")
