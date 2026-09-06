from app.tracking.violation_state_machine import ViolationStateMachine


def test_flags_after_debounce_window():
    sm = ViolationStateMachine(speed_limit_kmh=50, debounce_frames=3)
    assert sm.update(track_id=1, frame_index=0, speed_kmh=60) is None
    assert sm.update(track_id=1, frame_index=1, speed_kmh=62) is None
    result = sm.update(track_id=1, frame_index=2, speed_kmh=58)
    assert result is not None
    assert result.track_id == 1
    assert result.frame_index == 2
    assert result.speed_kmh == (60 + 62 + 58) / 3


def test_never_flags_below_debounce_window():
    sm = ViolationStateMachine(speed_limit_kmh=50, debounce_frames=5)
    for frame_index in range(4):
        assert sm.update(track_id=1, frame_index=frame_index, speed_kmh=99) is None


def test_dropping_below_limit_resets_the_streak():
    sm = ViolationStateMachine(speed_limit_kmh=50, debounce_frames=3)
    sm.update(track_id=1, frame_index=0, speed_kmh=60)
    sm.update(track_id=1, frame_index=1, speed_kmh=60)
    assert sm.update(track_id=1, frame_index=2, speed_kmh=40) is None  # back under limit, resets
    assert sm.update(track_id=1, frame_index=3, speed_kmh=60) is None  # streak restarts, only 1/3
    assert sm.update(track_id=1, frame_index=4, speed_kmh=60) is None  # 2/3
    result = sm.update(track_id=1, frame_index=5, speed_kmh=60)  # 3/3
    assert result is not None


def test_flags_at_most_once_per_track():
    sm = ViolationStateMachine(speed_limit_kmh=50, debounce_frames=2)
    sm.update(track_id=1, frame_index=0, speed_kmh=60)
    first = sm.update(track_id=1, frame_index=1, speed_kmh=60)
    assert first is not None
    # keeps reporting a high speed for many more frames - must stay silent
    for frame_index in range(2, 10):
        assert sm.update(track_id=1, frame_index=frame_index, speed_kmh=70) is None


def test_tracks_are_independent():
    sm = ViolationStateMachine(speed_limit_kmh=50, debounce_frames=2)
    sm.update(track_id=1, frame_index=0, speed_kmh=60)
    sm.update(track_id=2, frame_index=0, speed_kmh=30)  # under limit, unrelated track
    result1 = sm.update(track_id=1, frame_index=1, speed_kmh=60)
    result2 = sm.update(track_id=2, frame_index=1, speed_kmh=35)
    assert result1 is not None
    assert result2 is None
