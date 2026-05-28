import queue as q
import threading
from unittest.mock import patch

from playback.input_handler import _listen_loop, start_listening


# ── helper ───────────────────────────────────────────────────────────────────

def _run_with_keys(*keys: str) -> q.Queue:
    """Run _listen_loop with a fixed keypress sequence, then stop via KeyboardInterrupt.

    Returns the command queue so tests can inspect what was put in it.
    """
    cmd_queue = q.Queue()
    with patch("playback.input_handler._get_keypress") as mock_get:
        mock_get.side_effect = [*keys, KeyboardInterrupt]
        try:
            _listen_loop(cmd_queue)
        except KeyboardInterrupt:
            pass
    return cmd_queue


# ── tests ─────────────────────────────────────────────────────────────────────

def test_right_arrow_queues_skip():
    assert _run_with_keys("\x1b[C").get_nowait() == "SKIP"


def test_q_keypress_queues_quit():
    assert _run_with_keys("q").get_nowait() == "QUIT"


def test_space_first_press_queues_pause():
    assert _run_with_keys(" ").get_nowait() == "PAUSE"


def test_space_second_press_queues_resume():
    cmd_queue = _run_with_keys(" ", " ")
    assert cmd_queue.get_nowait() == "PAUSE"
    assert cmd_queue.get_nowait() == "RESUME"


def test_up_arrow_queues_vol_up():
    assert _run_with_keys("\x1b[A").get_nowait() == "VOL_UP"


def test_down_arrow_queues_vol_down():
    assert _run_with_keys("\x1b[B").get_nowait() == "VOL_DOWN"


def test_unknown_key_adds_nothing_to_queue():
    assert _run_with_keys("x").empty()


def test_left_arrow_queues_rewind():
    assert _run_with_keys("\x1b[D").get_nowait() == "REWIND"


def test_start_listening_returns_daemon_thread():
    with patch("playback.input_handler._listen_loop"):
        thread = start_listening(q.Queue())
    assert isinstance(thread, threading.Thread)
    assert thread.daemon is True
