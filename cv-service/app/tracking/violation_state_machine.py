"""Per-track violation dedup: NORMAL -> VIOLATING -> FLAGGED.

track_id already gives "same vehicle across frames" for free (Module 2), so
the only real job here is deciding WHEN a track's speed is confident enough
to flag - and making sure each track gets flagged at most once. Requiring N
consecutive over-threshold frames (not a single frame) is also what rejects
the Module 2 finding (static false-positive tracks with noisy, often-low
confidence) without needing a separate, unreliable heuristic for that - see
docs/models/tracking.md.
"""

from dataclasses import dataclass, field
from enum import Enum


class ViolationStatus(Enum):
    NORMAL = "normal"
    VIOLATING = "violating"
    FLAGGED = "flagged"


@dataclass
class TrackState:
    status: ViolationStatus = ViolationStatus.NORMAL
    consecutive_over_threshold: int = 0
    speeds_while_violating: list[float] = field(default_factory=list)


@dataclass
class FlaggedViolation:
    track_id: int
    frame_index: int
    speed_kmh: float  # average over the debounce window, not a single noisy sample


class ViolationStateMachine:
    def __init__(self, speed_limit_kmh: float, debounce_frames: int = 5):
        self.speed_limit_kmh = speed_limit_kmh
        self.debounce_frames = debounce_frames
        self._tracks: dict[int, TrackState] = {}

    def update(self, track_id: int, frame_index: int, speed_kmh: float) -> FlaggedViolation | None:
        """Feed one (track_id, speed) observation. Returns a FlaggedViolation
        the moment a track crosses into FLAGGED - None otherwise, including
        every subsequent call for a track that's already FLAGGED (terminal,
        emitted once)."""
        state = self._tracks.setdefault(track_id, TrackState())
        if state.status is ViolationStatus.FLAGGED:
            return None

        if speed_kmh > self.speed_limit_kmh:
            state.consecutive_over_threshold += 1
            state.speeds_while_violating.append(speed_kmh)
        else:
            state.consecutive_over_threshold = 0
            state.speeds_while_violating.clear()
            state.status = ViolationStatus.NORMAL
            return None

        if state.consecutive_over_threshold >= self.debounce_frames:
            state.status = ViolationStatus.FLAGGED
            avg_speed = sum(state.speeds_while_violating) / len(state.speeds_while_violating)
            return FlaggedViolation(track_id=track_id, frame_index=frame_index, speed_kmh=avg_speed)

        state.status = ViolationStatus.VIOLATING
        return None
