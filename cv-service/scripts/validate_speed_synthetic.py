"""Synthetic ground-truth check: build a known homography, simulate a point
moving at an exact known speed, and confirm speed_kmh_from_positions()
recovers it. Proves the geometry/math has no bugs, independent of any
detector/tracker noise or external dataset availability.

Usage: python scripts/validate_speed_synthetic.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from app.calibration.homography import Calibration, speed_kmh_from_positions

# A straight 3.5m-wide, 40m-long road segment, viewed at an angle typical of
# a roadside camera (far edge of the segment appears compressed/higher in
# frame - this is what makes the mapping a real homography, not identity).
IMAGE_POINTS = [
    (400, 900),  # near-left
    (900, 900),  # near-right
    (700, 300),  # far-right
    (600, 300),  # far-left
]
WORLD_POINTS = [
    (0.0, 0.0),
    (3.5, 0.0),
    (3.5, 40.0),
    (0.0, 40.0),
]

FPS = 30.0
KNOWN_SPEED_KMH = 72.0


def world_to_image(calibration: Calibration, point: tuple[float, float]) -> tuple[float, float]:
    inverse = np.linalg.inv(calibration.homography)
    inv_calibration = Calibration(homography=inverse)
    return inv_calibration.image_to_world(point)  # same math, just the inverse matrix


def main():
    calibration = Calibration.from_point_correspondences(IMAGE_POINTS, WORLD_POINTS)

    # simulate a vehicle travelling straight down the lane's centerline at
    # exactly KNOWN_SPEED_KMH, sampled every frame for 1 second
    speed_ms = KNOWN_SPEED_KMH / 3.6
    num_frames = int(FPS)  # 1 second of motion
    lane_x = 1.75  # centerline of the 3.5m-wide lane
    positions = []
    for frame_index in range(num_frames):
        t = frame_index / FPS
        world_point = (lane_x, 5.0 + speed_ms * t)  # start 5m into the segment
        image_point = world_to_image(calibration, world_point)
        positions.append((frame_index, image_point))

    recovered_speed = speed_kmh_from_positions(positions, calibration, FPS)
    error_pct = abs(recovered_speed - KNOWN_SPEED_KMH) / KNOWN_SPEED_KMH * 100

    print(f"known speed:     {KNOWN_SPEED_KMH:.4f} km/h")
    print(f"recovered speed: {recovered_speed:.4f} km/h")
    print(f"error:           {error_pct:.6f}%")

    assert error_pct < 0.01, f"synthetic validation failed: {error_pct:.4f}% error"
    print("\nPASS - speed math correctly recovers a known synthetic speed")


if __name__ == "__main__":
    main()
