
import cv2
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.core.auth import get_current_user
from app.services.video_stream_service import (
    VideoStreamService,
    STREAM_STATUS,
)


router = APIRouter(
    prefix="/api/video",
    tags=["Video"],
    dependencies=[Depends(get_current_user)],
)

VIDEO_PATH = "test_videos/test.mp4"

PHONE_RTSP_URL = (
    "rtsp://10.238.129.126:8080/h264_pcm.sdp"
)


def get_video_source(source: str):
    if source == "local":
        return VIDEO_PATH

    if source == "phone":
        return PHONE_RTSP_URL

    raise HTTPException(
        status_code=400,
        detail="Invalid source. Use 'local' or 'phone'."
    )


@router.get("/info")
def video_info(
    source: str = Query(default="phone")
):
    video_source = get_video_source(source)
    cap = cv2.VideoCapture(video_source)

    try:
        if not cap.isOpened():
            raise HTTPException(
                status_code=503,
                detail="Could not connect to the video source."
            )

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        return {
            "source": source,
            "width": width,
            "height": height,
            "fps": fps
        }

    finally:
        cap.release()

@router.get("/status")
def video_status(source: str = Query(default="phone")):
    get_video_source(source)  # Validate source.

    return {
        "source": source,
        **STREAM_STATUS[source],
    }

@router.get("/stream")
def video_stream(
    source: str = Query(default="phone")
):
    video_source = get_video_source(source)

    service = VideoStreamService(
        video_source=video_source,
        model_path="models/best.pt"
    )

    return StreamingResponse(
        service.generate_frames(),
        media_type=(
            "multipart/x-mixed-replace; boundary=frame"
        )
    )
