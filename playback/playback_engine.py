from __future__ import annotations

import logging
import queue
import time

import pygame

from config.settings import CROSSFADE_DURATION_SECS
from core.session_controller import (
    SessionState,
    advance_track,
    apply_command,
    current_track,
    is_complete,
)

logger = logging.getLogger("running_playlist")

_TICK_SECS = 0.1
_PRELOAD_AFTER_SECS = 5.0


def _load_sound(path: str):
    """Load a pygame Sound from path; log an error and return None on any failure."""
    try:
        return pygame.mixer.Sound(path)
    except FileNotFoundError:
        logger.error("Audio file not found: %s", path)
        return None
    except Exception as exc:
        logger.error("Failed to load audio file %s: %s", path, exc)
        return None


def _load_and_play(channel, track: dict, volume: float) -> bool:
    """Load and start playing a track on the given channel; return True on success."""
    sound = _load_sound(track["path"])
    if sound is None:
        return False
    channel.set_volume(volume)
    channel.play(sound)
    return True


def start(state: SessionState, command_queue: queue.Queue) -> None:
    """Run the playback loop on the calling thread until the session is complete.

    Blocks until state.is_complete is True. Initialises and tears down
    pygame.mixer internally.
    """
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    except pygame.error as e:
        raise RuntimeError(f"Audio device unavailable: {e}") from e

    ch_a = pygame.mixer.Channel(0)  # active channel
    ch_b = pygame.mixer.Channel(1)  # standby / crossfade incoming channel

    # Load and start the first available track, skipping any that fail to load
    while not is_complete(state):
        track = current_track(state)
        if _load_and_play(ch_a, track, state.volume):
            break
        logger.error("Skipping unloadable track: %s", track["path"])
        advance_track(state)

    if is_complete(state):
        pygame.mixer.stop()
        pygame.mixer.quit()
        logger.info("Playback complete.")
        return

    track_start_time = time.monotonic()
    crossfade_start_time: float | None = None
    was_paused = False
    next_sound: pygame.mixer.Sound | None = None

    try:
        while not is_complete(state):

            # ── 1. Drain command queue ────────────────────────────────────────
            index_before = state.current_index
            while True:
                try:
                    cmd = command_queue.get_nowait()
                    apply_command(state, cmd)
                    if cmd in ("VOL_UP", "VOL_DOWN"):
                        ch_a.set_volume(state.volume)
                        if crossfade_start_time is not None:
                            ch_b.set_volume(state.volume)
                except queue.Empty:
                    break

            # Rewind: stop and reload the appropriate track, then continue.
            if state.pending_action is not None:
                ch_a.stop()
                ch_b.stop()
                crossfade_start_time = None
                next_sound = None
                if not is_complete(state):
                    while not is_complete(state):
                        track = current_track(state)
                        if _load_and_play(ch_a, track, state.volume):
                            track_start_time = time.monotonic()
                            break
                        logger.error("Skipping unloadable track: %s", track["path"])
                        advance_track(state)
                state.pending_action = None
                state.elapsed_mins += _TICK_SECS / 60
                time.sleep(_TICK_SECS)
                continue

            # SKIP detection: advance_track was called inside apply_command —
            # stop the current track immediately and load the new one.
            if state.current_index != index_before:
                ch_a.stop()
                ch_b.stop()
                crossfade_start_time = None
                next_sound = None
                if not is_complete(state):
                    while not is_complete(state):
                        track = current_track(state)
                        if _load_and_play(ch_a, track, state.volume):
                            track_start_time = time.monotonic()
                            break
                        logger.error("Skipping unloadable track: %s", track["path"])
                        advance_track(state)
                state.elapsed_mins += _TICK_SECS / 60
                time.sleep(_TICK_SECS)
                continue

            # ── 2. Pause / resume ─────────────────────────────────────────────
            if state.is_paused:
                if not was_paused:
                    ch_a.pause()
                    if crossfade_start_time is not None:
                        ch_b.pause()
                    was_paused = True
                time.sleep(_TICK_SECS)
                continue
            if was_paused:
                ch_a.unpause()
                if crossfade_start_time is not None:
                    ch_b.unpause()
                was_paused = False

            # ── 3. Track / crossfade progression ──────────────────────────────
            elapsed = time.monotonic() - track_start_time

            if crossfade_start_time is not None:
                # Crossfade in progress — swap channels once it has fully elapsed
                if time.monotonic() - crossfade_start_time >= CROSSFADE_DURATION_SECS:
                    ch_a.stop()
                    ch_a, ch_b = ch_b, ch_a
                    advance_track(state)
                    # New track has been audible since crossfade_start_time
                    track_start_time = crossfade_start_time
                    crossfade_start_time = None
                    next_sound = None

            elif not ch_a.get_busy():
                # Track finished naturally (hardcut end or track ran to completion)
                advance_track(state)
                next_sound = None
                if not is_complete(state):
                    while not is_complete(state):
                        track = current_track(state)
                        if _load_and_play(ch_a, track, state.volume):
                            track_start_time = time.monotonic()
                            break
                        logger.error("Skipping unloadable track: %s", track["path"])
                        advance_track(state)

            elif state.transition_style == "crossfade":
                # Check whether to trigger a crossfade for the next track
                track = current_track(state)
                time_remaining = track["duration_secs"] - elapsed
                next_idx = state.current_index + 1

                # Pre-load the next track 5 seconds into the current one so it
                # is already in memory when the crossfade trigger point arrives.
                if (
                    next_sound is None
                    and elapsed >= _PRELOAD_AFTER_SECS
                    and next_idx < len(state.queue_dict["tracks"])
                ):
                    next_sound = _load_sound(state.queue_dict["tracks"][next_idx]["path"])

                if (
                    time_remaining <= CROSSFADE_DURATION_SECS
                    and next_idx < len(state.queue_dict["tracks"])
                ):
                    sound = next_sound or _load_sound(state.queue_dict["tracks"][next_idx]["path"])
                    if sound is not None:
                        fade_ms = int(CROSSFADE_DURATION_SECS * 1000)
                        ch_b.set_volume(state.volume)
                        ch_b.play(sound, fade_ms=fade_ms)
                        ch_a.fadeout(fade_ms)
                        crossfade_start_time = time.monotonic()

            # ── 4. Update elapsed time ────────────────────────────────────────
            state.elapsed_mins += _TICK_SECS / 60
            state.track_elapsed_secs += _TICK_SECS

            # ── 5. Sleep ──────────────────────────────────────────────────────
            time.sleep(_TICK_SECS)

    finally:
        pygame.mixer.stop()
        pygame.mixer.quit()
        logger.info("Playback complete.")
