import time

from app.streaming.frame_source import simulate_live


def test_paces_fast_processing_to_match_fps():
    # 5 frames at 10fps should take ~0.4s (frames 1-4 each wait, frame 0 is immediate)
    start = time.monotonic()
    result = list(simulate_live(range(5), fps=10.0))
    elapsed = time.monotonic() - start

    assert result == [0, 1, 2, 3, 4]
    assert 0.35 < elapsed < 0.6


def test_does_not_slow_down_processing_that_is_already_slower_than_fps():
    def slow_frames():
        for i in range(3):
            time.sleep(0.05)  # slower than the 1000fps target below
            yield i

    start = time.monotonic()
    result = list(simulate_live(slow_frames(), fps=1000.0))
    elapsed = time.monotonic() - start

    assert result == [0, 1, 2]
    # should take ~0.15s (the processing time), not be held back further -
    # a real live system falls behind under load, it doesn't get slower
    assert elapsed < 0.25
