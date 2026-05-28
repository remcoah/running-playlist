from __future__ import annotations

import logging
import queue
import sys
import termios
import threading
import tty

logger = logging.getLogger("running_playlist")


def _get_keypress() -> str:
    """Read one raw keypress from stdin, including multi-byte escape sequences for arrow keys."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            ch += sys.stdin.read(2)   # consume the two-byte arrow-key suffix
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
    try:
        while True:
            try:
                ch = _get_keypress()
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
                logger.error("Input read error: %s", exc)
    finally:
        if old_settings is not None:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except termios.error:
                pass


def start_listening(command_queue: queue.Queue) -> threading.Thread:
    """Start a daemon thread running _listen_loop and return it."""
    thread = threading.Thread(target=_listen_loop, args=(command_queue,), daemon=True)
    thread.start()
    return thread
