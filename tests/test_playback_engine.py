"""
Mock-based tests for playback_engine.start().

pygame does not need to be installed — a stub is injected into sys.modules
before the engine module is imported, and @patch replaces it per test.
"""
import sys
from unittest.mock import MagicMock, patch
import queue as q

# Provide a pygame stub so the module can be imported without pygame installed.
# setdefault leaves real pygame in place if it is already present.
sys.modules.setdefault("pygame", MagicMock())
sys.modules.setdefault("pygame.mixer", MagicMock())

import pytest  # noqa: E402 — must come after sys.modules setup

from config.settings import INITIAL_VOLUME, VOLUME_STEP
from core.session_controller import create_session
from playback.playback_engine import start


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_state(n: int = 2, transition: str = "hardcut"):
    qd = {
        "tracks": [
            {
                "path": f"/songs/track_{i}.mp3",
                "bpm": 150,
                "duration_secs": 300,
                "energy": 0.5,
            }
            for i in range(n)
        ],
        "target_bpm": 165,
        "profile": "steady",
        "total_duration_secs": n * 300,
        "generated_at": "2026-01-01T00:00:00+00:00",
        "warmup_count": 0,
        "cooldown_count": 0,
    }
    return create_session(qd, transition)


def _busy_channel():
    """Return a mock Channel whose get_busy() always returns True (track playing)."""
    ch = MagicMock()
    ch.get_busy.return_value = True
    return ch


# ── tests ─────────────────────────────────────────────────────────────────────

@patch("playback.playback_engine.pygame")
@patch("playback.playback_engine.time")
def test_start_drains_command_queue(mock_time, mock_pygame):
    """All commands placed in the queue are consumed and applied before start() returns."""
    state = _make_state()
    cmd_queue = q.Queue()
    cmd_queue.put("PAUSE")
    cmd_queue.put("RESUME")
    cmd_queue.put("QUIT")

    mock_pygame.mixer.Channel.return_value = _busy_channel()
    mock_pygame.mixer.Sound.return_value = MagicMock()
    mock_time.monotonic.return_value = 0.0

    start(state, cmd_queue)

    assert cmd_queue.empty(), "queue must be fully drained"
    assert state.is_complete is True
    assert state.is_paused is False  # PAUSE then RESUME both applied


@patch("playback.playback_engine.pygame")
@patch("playback.playback_engine.time")
def test_quit_causes_loop_to_exit(mock_time, mock_pygame):
    """A QUIT command sets is_complete and start() returns; pygame is torn down."""
    state = _make_state()
    cmd_queue = q.Queue()
    cmd_queue.put("QUIT")

    mock_pygame.mixer.Channel.return_value = _busy_channel()
    mock_pygame.mixer.Sound.return_value = MagicMock()
    mock_time.monotonic.return_value = 0.0

    start(state, cmd_queue)

    assert state.is_complete is True
    mock_pygame.mixer.stop.assert_called()
    mock_pygame.mixer.quit.assert_called()


@patch("playback.playback_engine.logger")
@patch("playback.playback_engine.pygame")
@patch("playback.playback_engine.time")
def test_file_not_found_logs_error_and_advances_track(mock_time, mock_pygame, mock_logger):
    """A missing audio file is logged and the track is skipped; no exception is raised."""
    state = _make_state(n=1)  # single track — after skipping it, session completes

    mock_pygame.mixer.Sound.side_effect = FileNotFoundError("no such file")
    mock_pygame.mixer.Channel.return_value = MagicMock()
    mock_time.monotonic.return_value = 0.0

    start(state, q.Queue())

    assert state.is_complete is True
    assert mock_logger.error.called


@patch("playback.playback_engine.pygame")
@patch("playback.playback_engine.time")
def test_vol_up_immediately_updates_channel_volume(mock_time, mock_pygame):
    """VOL_UP applies the new volume to the active channel in the same loop iteration."""
    state = _make_state()
    cmd_queue = q.Queue()
    cmd_queue.put("VOL_UP")
    cmd_queue.put("QUIT")

    mock_ch_a = _busy_channel()
    mock_ch_b = _busy_channel()
    mock_pygame.mixer.Channel.side_effect = [mock_ch_a, mock_ch_b]
    mock_pygame.mixer.Sound.return_value = MagicMock()
    mock_time.monotonic.return_value = 0.0

    start(state, cmd_queue)

    expected = min(1.0, round(INITIAL_VOLUME + VOLUME_STEP, 10))
    mock_ch_a.set_volume.assert_called_with(expected)
