import cv2

url = "rtsp://10.238.129.126:8080/h264_pcm.sdp"

cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)

if not cap.isOpened():
    print("FAILED: OpenCV could not open the RTSP stream.")
else:
    print("CONNECTED: RTSP stream opened successfully.")

    for i in range(30):
        success, frame = cap.read()

        if success:
            print(f"Frame {i + 1}: {frame.shape}")
            break

    else:
        print("CONNECTED, but no video frame was received.")

cap.release()
