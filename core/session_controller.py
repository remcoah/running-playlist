from __future__ import annotations

import logging
from dataclasses import dataclass

from config.settings import INITIAL_VOLUME, REWIND_THRESHOLD_SECS, VOLUME_STEP

logger = logging.getLogger("running_playlist")


@dataclass
class SessionState:
    queue_dict: dict
    current_index: int
    is_paused: bool
    elapsed_mins: float
    transition_style: str
    volume: float
    is_complete: bool
    track_elapsed_secs: float = 0.0
    pending_action: str | None = None


def create_session(queue_dict: dict, transition_style: str) -> SessionState:
    """Return a fresh SessionState for the given playlist and transition style.

    Raises ValueError if queue_dict has no tracks key or an empty tracks list.
    """
    tracks = queue_dict.get("tracks")
    if not tracks:
        raise ValueError(
            "queue_dict must contain a non-empty 'tracks' list."
        )
    return SessionState(
        queue_dict=queue_dict,
        current_index=0,
        is_paused=False,
        elapsed_mins=0.0,
        transition_style=transition_style,
        volume=INITIAL_VOLUME,
        is_complete=False,
    )


def current_track(state: SessionState) -> dict:
    """Return the track at state.current_index.

    Raises IndexError if current_index is out of range.
    """
    tracks = state.queue_dict["tracks"]
    if state.current_index >= len(tracks):
        raise IndexError(
            f"current_index {state.current_index} is out of range "
            f"(playlist has {len(tracks)} tracks)."
        )
    return tracks[state.current_index]


def advance_track(state: SessionState) -> SessionState:
    """Increment current_index and mark the session complete if the last track was passed."""
    state.current_index += 1
    state.track_elapsed_secs = 0.0
    if state.current_index >= len(state.queue_dict["tracks"]):
        state.is_complete = True
    return state


def rewind_track(state: SessionState) -> tuple[SessionState, str]:
    """Return updated state and an action string for playback_engine.

    'RESTART' — reload and replay the current track from the beginning.
    'LOAD_PREV' — stop current track and load the previous one.
    """
    if state.track_elapsed_secs > REWIND_THRESHOLD_SECS:
        state.track_elapsed_secs = 0.0
        return state, "RESTART"
    if state.current_index > 0:
        state.current_index -= 1
        state.track_elapsed_secs = 0.0
        return state, "LOAD_PREV"
    state.track_elapsed_secs = 0.0
    return state, "RESTART"


def is_complete(state: SessionState) -> bool:
    """Return True if the session has finished."""
    return state.is_complete


def get_summary(state: SessionState) -> dict:
    """Return a snapshot of session progress for display and post-run bookkeeping."""
    return {
        "tracks_played": min(
            state.current_index + 1,
            len(state.queue_dict["tracks"]),
        ),
        "elapsed_mins": state.elapsed_mins,
        "played_paths": [
            t["path"] for t in state.queue_dict["tracks"][: state.current_index]
        ],
    }


def apply_command(state: SessionState, command: str) -> SessionState:
    """Apply a command string to the session state and return the mutated state.

    Supported commands: PAUSE, RESUME, SKIP, REWIND, VOL_UP, VOL_DOWN, QUIT.
    Unknown commands are logged and ignored.
    """
    if command == "PAUSE":
        state.is_paused = True
    elif command == "RESUME":
        state.is_paused = False
    elif command == "SKIP":
        advance_track(state)
    elif command == "REWIND":
        _, action = rewind_track(state)
        state.pending_action = action
    elif command == "VOL_UP":
        state.volume = min(1.0, round(state.volume + VOLUME_STEP, 10))
    elif command == "VOL_DOWN":
        state.volume = max(0.0, round(state.volume - VOLUME_STEP, 10))
    elif command == "QUIT":
        state.is_complete = True
    else:
        logger.warning("apply_command: unknown command %r — state unchanged.", command)
    return state
