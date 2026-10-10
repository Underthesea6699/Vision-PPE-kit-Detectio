
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

    print("Starting helmet detection and tracking...")
    print(f"Input video: {VIDEO_PATH}")

    # Find the class ID for helmet.
    helmet_class_ids = [
        class_id
        for class_id, class_name in model.names.items()
        if class_name.strip().lower().replace("_", "-") == "helmet"
    ]

    if not helmet_class_ids:
        raise ValueError(
            f"Helmet class not found. Available classes: {model.names}"
        )

    print(f"Hemlet class ID(s): {helmet_class_ids}")

    model.track(
        source=str(VIDEO_PATH),
        tracker="bytetrack.yaml",
        persist=True,

        # Detect helmets only
        classes=helmet_class_ids,

        # YOLO detection settings
        imgsz=640,
        conf=0.20,
        iou=0.45,
        max_det=100,

        # Video output
        save=True,
        save_frames=False,
        project=str(OUTPUT_DIR),
        name="helmet_only",
        exist_ok=True,
        show=False,
        verbose=False,

        # Show class label and confidence
        show_labels=True,
        show_conf=True,
    )

    print("Helmet tracking completed.")
    print(f"Check the output folder: {OUTPUT_DIR / 'helmet_only'}")


if __name__ == "__main__":
    main()
