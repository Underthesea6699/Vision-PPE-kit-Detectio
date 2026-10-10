
from pathlib import Path
from ultralytics import YOLO

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "models" / "best.pt"
VIDEO_PATH = PROJECT_ROOT / "test_videos" / "test.mp4"
OUTPUT_DIR = PROJECT_ROOT / "runs" / "tracking"

def main():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

    if not VIDEO_PATH.exists():
        raise FileNotFoundError(f"Video not found: {VIDEO_PATH}")

    model = YOLO(str(MODEL_PATH))

    print("Starting object detection and tracking...")
    print(f"Input video: {VIDEO_PATH}")

    
    model.track(
        source=str(VIDEO_PATH),
        tracker="bytetrack.yaml",
        persist=True,

        # YOLO detection settings
        imgsz=640,
        conf=0.20,
        iou=0.45,
        max_det=100,

        # Video output
        save=True,
        save_frames=False,
        project=str(OUTPUT_DIR),
        name="tracked_test",
        exist_ok=True,
        show=False,
        verbose=False
    )


    print("Tracking completed.")
    print(f"Check the output folder: {OUTPUT_DIR / 'tracked_test'}")

if __name__ == "__main__":
    main()
