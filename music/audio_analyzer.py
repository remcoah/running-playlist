from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import librosa
import numpy as np

from config.settings import SONG_LIBRARY_PATH

logger = logging.getLogger("running_playlist")

SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".wav", ".m4a", ".ogg", ".aiff"}


def _analyze_file(file_path: Path) -> dict:
    """Load a single audio file and return its BPM, duration, and raw RMS energy."""
    # librosa requires a str path in some versions — convert from Path explicitly
    y, sr = librosa.load(str(file_path), sr=None, mono=True)

    # Detect tempo (BPM) from beat positions; we discard the beat frame array
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    # atleast_1d handles librosa versions that return a scalar vs an array
    bpm = int(round(float(np.atleast_1d(tempo)[0])))

    duration_secs = int(librosa.get_duration(y=y, sr=sr))

    # Store mean RMS as raw amplitude — normalisation happens at read time
    rms = librosa.feature.rms(y=y)[0]
    raw_energy = float(np.mean(rms))

    return {
        "path": str(file_path),  # stored as string in JSON; always absolute
        "bpm": bpm,
        "duration_secs": duration_secs,
        "energy": raw_energy,
        "last_played": None,
    }


def _normalise_energy(songs: list[dict]) -> list[dict]:
    """Rescale energy values to 0.0–1.0 relative to the loudest track in the list."""
    max_rms = max((s["energy"] for s in songs), default=1.0) or 1.0
    for song in songs:
        song["energy"] = round(song["energy"] / max_rms, 3)
    return songs


def scan_folder(folder_path: str) -> None:
    """Walk a folder, analyse any new audio files, and write raw RMS values to song_library.json."""
    # Resolve to absolute immediately so all stored paths are absolute regardless
    # of the working directory the caller used
    folder = Path(folder_path).resolve()

    if not folder.exists():
        raise FileNotFoundError(folder)

    # Index existing library by path so we can skip re-analysing known files
    existing = {song["path"]: song for song in _load_raw()}
    songs = list(existing.values())
    new_found = 0

    for root, _, files in os.walk(folder):
        for fname in sorted(files):
            if Path(fname).suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            new_found += 1
            full_path = (Path(root) / fname).resolve()
            key = str(full_path)
            if key not in existing:
                try:
                    songs.append(_analyze_file(full_path))
                except Exception as exc:
                    logger.warning("Could not analyse %s: %s", full_path, exc)

    if new_found == 0 and not existing:
        raise ValueError(folder)

    SONG_LIBRARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SONG_LIBRARY_PATH, "w") as f:
        json.dump(songs, f, indent=2)


def _load_raw() -> list[dict]:
    """Read song_library.json and return songs with their stored (raw) energy values."""
    if not SONG_LIBRARY_PATH.exists():
        return []
    with open(SONG_LIBRARY_PATH) as f:
        return json.load(f)


def get_library() -> list[dict]:
    """Read song_library.json and return songs with energy normalised across the full library."""
    songs = _load_raw()
    return _normalise_energy(songs) if songs else songs


def mark_played(paths: list[str]) -> None:
    """Set last_played to now for each path in the list, then write the update to song_library.json."""
    songs = _load_raw()
    index = {song["path"]: song for song in songs}
    now = datetime.now(timezone.utc).isoformat()

    for path in paths:
        if path not in index:
            logger.warning("mark_played: path not found in library, skipping: %s", path)
            continue
        index[path]["last_played"] = now

    with open(SONG_LIBRARY_PATH, "w") as f:
        json.dump(songs, f, indent=2)
