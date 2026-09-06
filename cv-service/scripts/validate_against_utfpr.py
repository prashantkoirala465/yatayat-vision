"""Validate the tracking+calibration+speed pipeline end-to-end against real
radar-measured ground truth from the UTFPR vehicle speed dataset (Luvizon
et al., IEEE T-ITS 2017) - not just the isolated math (see
validate_speed_synthetic.py for that), the actual detector+tracker output
run through the same Calibration/speed code used elsewhere in this project.

For each ground-truth vehicle (a radar-measured speed over a known frame
window and a single reference bbox), finds the closest-matching track from
a cached tracking run (see utfpr_cache_tracks.py) by spatial proximity to
that reference bbox, then computes speed over that track's positions within
the radar window and compares to the radar-measured value.

Usage:
    python scripts/validate_against_utfpr.py \\
        --tracks /tmp/utfpr_check/tracks.json \\
        --vehicles /tmp/utfpr_check/vehicles.xml \\
        --matrices /tmp/utfpr_check/matrix.txt \\
        --fps 30.0
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json

import numpy as np

from app.calibration.homography import Calibration, bbox_bottom_center, speed_kmh_from_positions

FRAME_BUFFER = 3  # small tolerance around frame_start/frame_end for tracker misalignment


def load_matrices(path: str) -> dict[int, Calibration]:
    """matrix.txt has one blank-line-separated 3x3 matrix per lane, in lane order (1,2,3)."""
    text = Path(path).read_text().strip()
    blocks = [b for b in text.split("\n\n") if b.strip()]
    calibrations = {}
    for lane_index, block in enumerate(blocks, start=1):
        rows = [[float(v) for v in line.split()] for line in block.strip().splitlines()]
        calibrations[lane_index] = Calibration.from_matrix(np.array(rows))
    return calibrations


def load_ground_truth(path: str):
    root = ET.parse(path).getroot()
    out = []
    for v in root.findall(".//vehicle"):
        radar = v.find("radar")
        if radar is None:
            continue
        region = v.find("region")
        out.append(
            {
                "iframe": int(v.get("iframe")),
                "lane": int(v.get("lane")),
                "region": (float(region.get("x")), float(region.get("y")), float(region.get("w")), float(region.get("h"))),
                "frame_start": int(radar.get("frame_start")),
                "frame_end": int(radar.get("frame_end")),
                "speed": float(radar.get("speed")),
            }
        )
    return out


def load_tracks(path: str) -> dict[int, list[dict]]:
    """Returns frame_index -> list of detections, for fast lookup by frame."""
    frames = json.loads(Path(path).read_text())
    return {f["frame"]: f["detections"] for f in frames}


def region_xyxy(region: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    x, y, w, h = region
    return x, y, x + w, y + h


def iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


MIN_MATCH_IOU = 0.3


def find_matching_track_id(gt: dict, tracks_by_frame: dict[int, list[dict]]) -> int | None:
    """Matches by IoU, not just center proximity - a nearby detection of a
    completely different size (e.g. a different vehicle, or tracking noise)
    can have a close center but should never count as the same object."""
    target = region_xyxy(gt["region"])
    best_id, best_iou = None, MIN_MATCH_IOU
    for frame in range(gt["iframe"] - FRAME_BUFFER, gt["iframe"] + FRAME_BUFFER + 1):
        for det in tracks_by_frame.get(frame, []):
            score = iou(tuple(det["xyxy"]), target)
            if score > best_iou:
                best_iou, best_id = score, det["track_id"]
    return best_id


def positions_for_track(track_id: int, frame_start: int, frame_end: int, tracks_by_frame: dict[int, list[dict]]):
    positions = []
    for frame in range(frame_start, frame_end + 1):
        for det in tracks_by_frame.get(frame, []):
            if det["track_id"] == track_id:
                positions.append((frame, bbox_bottom_center(tuple(det["xyxy"]))))
                break
    return positions


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tracks", required=True)
    parser.add_argument("--vehicles", required=True)
    parser.add_argument("--matrices", required=True)
    parser.add_argument("--fps", type=float, default=30.0)
    args = parser.parse_args()

    calibrations = load_matrices(args.matrices)
    ground_truth = load_ground_truth(args.vehicles)
    tracks_by_frame = load_tracks(args.tracks)

    print(f"ground-truth vehicles: {len(ground_truth)}")

    results = []
    unmatched = 0
    for gt in ground_truth:
        track_id = find_matching_track_id(gt, tracks_by_frame)
        if track_id is None:
            unmatched += 1
            continue
        positions = positions_for_track(track_id, gt["frame_start"], gt["frame_end"], tracks_by_frame)
        if len(positions) < 2:
            unmatched += 1
            continue
        calibration = calibrations[gt["lane"]]
        computed = speed_kmh_from_positions(positions, calibration, args.fps)
        results.append({"gt_speed": gt["speed"], "computed_speed": computed, "lane": gt["lane"], "n_positions": len(positions)})

    print(f"matched: {len(results)}, unmatched (no track found / too few positions): {unmatched}")

    if not results:
        print("no matches - nothing to score")
        return

    errors = [abs(r["computed_speed"] - r["gt_speed"]) for r in results]
    pct_errors = [abs(r["computed_speed"] - r["gt_speed"]) / r["gt_speed"] * 100 for r in results]
    mae = sum(errors) / len(errors)
    mape = sum(pct_errors) / len(pct_errors)

    print(f"\nMAE:  {mae:.2f} km/h")
    print(f"MAPE: {mape:.1f}%")
    print("\nsample (gt -> computed, |error|):")
    for r in sorted(results, key=lambda r: -abs(r["computed_speed"] - r["gt_speed"]))[:10]:
        err = abs(r["computed_speed"] - r["gt_speed"])
        print(f"  lane {r['lane']}: {r['gt_speed']:.1f} -> {r['computed_speed']:.1f} km/h (|err| {err:.1f}, n={r['n_positions']})")


if __name__ == "__main__":
    main()
