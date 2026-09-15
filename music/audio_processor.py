from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

from config.settings import (
    MAX_STRETCH_RATIO,
    MIN_STRETCH_RATIO,
    PROCESSING_TIME_MULTIPLIER,
    STRETCH_SAME_BPM_THRESHOLD,
)

logger = logging.getLogger("running_playlist")


class AudioProcessingError(Exception):
    pass


def _convert_to_wav(source_path: str, temp_wav: Path) -> None:
    """Convert source_path to temp_wav via ffmpeg.

    librosa.load falls back to the audioread/CoreAudio backend for formats
    libsndfile can't decode (e.g. most MP3s), and repeated audioread calls
    in one process are unstable on macOS. Pre-converting to WAV keeps every
    librosa.load call on the libsndfile path instead.
    """
    filename = Path(source_path).name
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", source_path, "-ar", "44100", str(temp_wav)],
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise AudioProcessingError(
            f"Could not convert {filename}: ffmpeg is not installed. "
            f"Install it with 'brew install ffmpeg'."
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode(errors="replace") if exc.stderr else str(exc)
        raise AudioProcessingError(f"Could not convert {filename} to WAV: {stderr}") from exc


def stretch_track(source_path: str, original_bpm: float, target_bpm: float, temp_dir: Path) -> Path:
    """Time-stretch a track to the target BPM and write it to temp_dir, or return the original path unmodified if stretching isn't needed or the ratio is out of bounds."""
    filename = Path(source_path).name

    if original_bpm <= 0:
        raise AudioProcessingError(
            f"Invalid original_bpm ({original_bpm}) for "
            f"{Path(source_path).name} — cannot calculate stretch ratio"
        )

    ratio = target_bpm / original_bpm

    if ratio < MIN_STRETCH_RATIO or ratio > MAX_STRETCH_RATIO:
        logger.warning("BPM ratio %.2f outside bounds for %s — playing original", ratio, filename)
        return Path(source_path)

    if abs(ratio - 1.0) < STRETCH_SAME_BPM_THRESHOLD:
        return Path(source_path)

    temp_wav = temp_dir / f"{Path(source_path).stem}_source.wav"
    try:
        _convert_to_wav(source_path, temp_wav)

        try:
            y, sr = librosa.load(str(temp_wav), sr=None, mono=False)
        except Exception as exc:
            raise AudioProcessingError(f"Could not load {filename} for stretching: {exc}") from exc

        try:
            # time_stretch only accepts 1D input — stretch each channel separately
            # so stereo output is preserved rather than downmixing to mono first
            if y.ndim == 2:
                stretched = np.stack(
                    [librosa.effects.time_stretch(channel, rate=ratio) for channel in y],
                    axis=0,
                )
            else:
                stretched = librosa.effects.time_stretch(y, rate=ratio)
        except Exception as exc:
            raise AudioProcessingError(f"Could not time-stretch {filename}: {exc}") from exc

        out_path = temp_dir / f"{Path(source_path).stem}_{int(target_bpm)}bpm.wav"
        try:
            # soundfile expects (samples, channels); librosa gives (channels, samples)
            data = stretched.T if stretched.ndim == 2 else stretched
            sf.write(str(out_path), data, sr)
        except Exception as exc:
            raise AudioProcessingError(f"Could not write stretched output for {filename}: {exc}") from exc
    finally:
        temp_wav.unlink(missing_ok=True)

    return out_path


def estimate_processing_time(tracks: list[dict]) -> float:
    """Estimate total seconds required to stretch all tracks, without doing any actual processing."""
    return sum(t["duration_secs"] for t in tracks) * PROCESSING_TIME_MULTIPLIER
