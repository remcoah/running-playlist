"""Reads raw keypresses on a background thread and turns them into playback commands."""

from __future__ import annotations

import logging
import queue
import sys
import termios
import threading
import time
import tty

logger = logging.getLogger("running_playlist")

_original_terminal_settings = None

# If stdin isn't a real TTY (e.g. running under a non-interactive process),
# every read fails immediately and repeatedly — without these, the loop
# spins as fast as the CPU allows and floods the log.
_MAX_CONSECUTIVE_READ_FAILURES = 10
_READ_FAILURE_BACKOFF_SECS = 0.5


def restore_terminal() -> None:
    """Restore the terminal to the settings captured at start_listening() time.

    Safe to call from any thread, any number of times, even if the terminal
    is already restored or stdin is closed.
    """
    if _original_terminal_settings is not None:
        try:
            termios.tcsetattr(
                sys.stdin.fileno(), termios.TCSADRAIN, _original_terminal_settings,
            )
        except Exception:
            pass


def _get_keypress() -> str:
    """Read one raw keypress from stdin, including multi-byte escape sequences for arrow keys."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            ch += sys.stdin.read(2)  # consume the two-byte arrow-key suffix
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _listen_loop(command_queue: queue.Queue) -> None:
    """Read keypresses forever and drop command strings into command_queue."""
    _is_paused = False
    fd = None
    old_settings = None
    try:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
    except Exception:
        pass
    consecutive_failures = 0
    try:
        while True:
            try:
                ch = _get_keypress()
                consecutive_failures = 0
                if ch == " ":
                    if _is_paused:
                        command_queue.put("RESUME")
                        _is_paused = False
                    else:
                        command_queue.put("PAUSE")
                        _is_paused = True
                elif ch == "\x1b[C":
                    command_queue.put("SKIP")
                elif ch == "\x1b[D":
                    command_queue.put("REWIND")
                elif ch == "\x1b[A":
                    command_queue.put("VOL_UP")
                elif ch == "\x1b[B":
                    command_queue.put("VOL_DOWN")
                elif ch in ("q", "Q"):
                    command_queue.put("QUIT")
                # Unknown keys are silently ignored
            except Exception as exc:
                consecutive_failures += 1
                logger.error("Input read error: %s", exc)
                if consecutive_failures >= _MAX_CONSECUTIVE_READ_FAILURES:
                    logger.error(
                        "Input listener giving up after %d consecutive read "
                        "failures — stdin may not be a real terminal. "
                        "Keyboard controls are disabled for this run.",
                        consecutive_failures,
                    )
                    return
                time.sleep(_READ_FAILURE_BACKOFF_SECS)
    finally:
        if old_settings is not None:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except termios.error:
                pass


def start_listening(command_queue: queue.Queue) -> threading.Thread:
    """Start a daemon thread running _listen_loop and return it."""
    global _original_terminal_settings
    try:
        fd = sys.stdin.fileno()
        _original_terminal_settings = termios.tcgetattr(fd)
    except Exception:
        pass
    thread = threading.Thread(target=_listen_loop, args=(command_queue,), daemon=True)
    thread.start()
    return thread
