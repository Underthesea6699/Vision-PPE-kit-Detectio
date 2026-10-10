from ultralytics import YOLO


# Load the pretrained YOLOv8 nano model
model = YOLO("yolov8n.pt")

# Run detection
results = model("test_images/test.jpg")

# Display detection information
for result in results:
    print("\nDetected objects:")

    for box in result.boxes:
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])
        class_name = result.names[class_id]

        print(
            f"Object: {class_name} | "
            f"Confidence: {confidence:.2f}"
        )

    # Save image with bounding boxes
    result.save(filename="test_images/result.jpg")

print("\nDetection completed.")
print("Annotated image saved to: test_images/result.jpg")