"""RQ job that runs the video-processing pipeline in the background."""

from app.calibration.homography import Calibration
from app.pipeline import PipelineConfig, process_video

# Same illustrative calibration as scripts/violation_demo.py - see
# docs/models/speed_estimation.md for why real-world calibration validation
# is deferred rather than faked. A real deployment would look up a real,
# per-camera calibration by source_id instead of using one fixed set of
# points - not needed until a real calibrated camera exists (Module 7+).
IMAGE_POINTS = [(192, 2150), (1839, 2150), (1344, 758), (1834, 730)]
WORLD_POINTS = [(0.0, 0.0), (7.0, 0.0), (0.0, 100.0), (7.0, 100.0)]


def process_video_job(
    source_path: str, source_id: str, speed_limit_kmh: float, fps: float = 25.0, simulate_live: bool = False
) -> int:
    calibration = Calibration.from_point_correspondences(IMAGE_POINTS, WORLD_POINTS)
    config = PipelineConfig(
        vehicle_model_path="data/models/best.pt",
        plate_model_path="data/models/plate_detector.pt",
        calibration=calibration,
        fps=fps,
        speed_limit_kmh=speed_limit_kmh,
        simulate_live=simulate_live,
    )
    return process_video(source_path, source_id, config)
