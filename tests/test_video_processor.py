from app.vision.video_processor import VideoProcessor


VIDEO_PATH = "test_videos/test.mp4"


RESTRICTED_ZONE = [
    (118, 963),
    (129, 404),
    (505, 413),
    (490, 950)
]


processor = VideoProcessor(
    video_source=VIDEO_PATH,
    restricted_zone=RESTRICTED_ZONE
)

processor.process()