"""Where frames come from: a local file, a real RTSP/HLS stream, or a
recorded file paced to arrive like one - the Module 7 "simulated live"
fallback for public demos, per the project plan.

Ultralytics' own `.track(source=...)` already dispatches a file path or an
rtsp://, rtmp://, http(s):// URL to the right loader natively
(LoadImagesAndVideos vs LoadStreams - confirmed by reading
ultralytics.data.build.load_inference_source directly, not assumed) - so
VehicleTracker already handles both cases with zero new code. The one
capability nothing else provides is making a recorded file *behave* like a
live feed, which is what simulate_live() does.
"""

import time
from collections.abc import Iterator
from typing import TypeVar

T = TypeVar("T")


def simulate_live(frames: Iterator[T], fps: float) -> Iterator[T]:
    """Paces a recorded-file frame stream so it arrives no faster than real
    playback speed - it will not arrive faster, but if processing genuinely
    can't keep up with `fps` (slow hardware, heavy models), frames simply
    take as long as they take. That's not a bug to hide: it's exactly how a
    real live system behaves under load, and pretending otherwise here would
    misrepresent what "live" actually means for this pipeline.
    """
    start = time.monotonic()
    for frame_index, item in enumerate(frames):
        target_time = frame_index / fps
        elapsed = time.monotonic() - start
        if elapsed < target_time:
            time.sleep(target_time - elapsed)
        yield item
