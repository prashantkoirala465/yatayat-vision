"""Image-pixel to real-world ground-plane mapping, and speed from a tracked
point sequence. See docs/models/speed_estimation.md for how this was
validated (synthetically, and against real radar-measured ground truth).

Known simplification: this assumes a flat road plane and a pinhole model
with no lens-distortion correction - fine for an MVP, not a survey-grade
measurement. See the plan's documented limitations.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Calibration:
    """Wraps a 3x3 homography mapping image pixels to real-world ground-plane
    coordinates (in meters)."""

    homography: np.ndarray  # 3x3

    @classmethod
    def from_point_correspondences(
        cls, image_points: list[tuple[float, float]], world_points: list[tuple[float, float]]
    ) -> "Calibration":
        """The production path: derive a homography from >=4 manually-picked
        image points paired with their known real-world coordinates (e.g.
        measured lane-marking distances)."""
        if len(image_points) < 4 or len(image_points) != len(world_points):
            raise ValueError("need >=4 image/world point pairs, same length")
        h, _ = cv2.findHomography(np.array(image_points, dtype=np.float64), np.array(world_points, dtype=np.float64))
        return cls(homography=h)

    @classmethod
    def from_matrix(cls, matrix: np.ndarray) -> "Calibration":
        """Load an already-computed homography directly - used to validate
        the speed math against a dataset that ships its own calibration."""
        return cls(homography=np.asarray(matrix, dtype=np.float64))

    def image_to_world(self, point: tuple[float, float]) -> tuple[float, float]:
        px = np.array([[[point[0], point[1]]]], dtype=np.float64)
        world = cv2.perspectiveTransform(px, self.homography)
        return float(world[0, 0, 0]), float(world[0, 0, 1])


def bbox_bottom_center(xyxy: tuple[float, float, float, float]) -> tuple[float, float]:
    """The point of a vehicle that's actually on the road plane - a bbox's
    top is the roof, not the ground contact point."""
    x1, y1, x2, y2 = xyxy
    return (x1 + x2) / 2, y2


def speed_kmh_from_positions(
    positions: list[tuple[int, tuple[float, float]]], calibration: Calibration, fps: float
) -> float:
    """Average speed (km/h) over a tracked point sequence.

    positions: [(frame_index, image_point), ...], at least 2 entries, in
    time order. Uses first-to-last displacement, not a sum of per-step
    distances - a track's per-frame jitter would otherwise inflate a
    piecewise-summed distance well above the vehicle's actual net motion.
    """
    if len(positions) < 2:
        raise ValueError("need at least 2 positions to compute a speed")

    first_frame, first_point = positions[0]
    last_frame, last_point = positions[-1]
    if last_frame == first_frame:
        raise ValueError("positions span zero frames")

    x0, y0 = calibration.image_to_world(first_point)
    x1, y1 = calibration.image_to_world(last_point)
    distance_m = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    elapsed_s = (last_frame - first_frame) / fps
    return (distance_m / elapsed_s) * 3.6
