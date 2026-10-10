import cv2


VIDEO_PATH = "test_videos/test.mp4"

# Store clicked polygon points
points = []


def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append((x, y))
        print(f"Point {len(points)}: ({x}, {y})")


# Open video
cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():
    print(f"Could not open video: {VIDEO_PATH}")
    exit()


# Read the first frame
success, frame = cap.read()

cap.release()

if not success:
    print("Could not read the video frame.")
    exit()


window_name = "Select Restricted Zone"

cv2.namedWindow(window_name)
cv2.setMouseCallback(window_name, mouse_callback)


while True:

    display_frame = frame.copy()

    # Draw selected points
    for i, point in enumerate(points):

        cv2.circle(
            display_frame,
            point,
            6,
            (0, 0, 255),
            -1
        )

        # Draw point number
        cv2.putText(
            display_frame,
            str(i + 1),
            (point[0] + 10, point[1] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2
        )

    # Draw polygon when we have at least 2 points
    if len(points) >= 2:

        for i in range(len(points) - 1):

            cv2.line(
                display_frame,
                points[i],
                points[i + 1],
                (255, 0, 0),
                2
            )

    # Close polygon visually when 3+ points exist
    if len(points) >= 3:

        cv2.line(
            display_frame,
            points[-1],
            points[0],
            (255, 0, 0),
            2
        )

    cv2.imshow(window_name, display_frame)

    key = cv2.waitKey(1) & 0xFF

    # Press S to save
    if key == ord("s"):

        if len(points) < 3:

            print("Select at least 3 points.")

        else:

            print("\nRestricted Zone Coordinates:")

            print(points)

            with open("restricted_zone.txt", "w") as file:
                file.write(str(points))

            print("\nSaved to restricted_zone.txt")
            break

    # Press R to reset
    elif key == ord("r"):

        points.clear()
        print("Points cleared.")

    # Press Q to quit
    elif key == ord("q"):

        print("Cancelled.")
        break


cv2.destroyAllWindows()