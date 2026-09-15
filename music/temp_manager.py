"""Creates and cleans up the temp directory used for time-stretched audio output."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from config.settings import BASE_DIR, TEMP_DIR_NAME

logger = logging.getLogger("running_playlist")

_initialized = False


def setup() -> Path:
    """Create the temp stretch directory for this run, clearing any stale content left by a prior ungraceful exit, and return its Path."""
    global _initialized
    temp_dir = BASE_DIR / TEMP_DIR_NAME
    try:
        if temp_dir.exists():
            stale_count = sum(1 for p in temp_dir.rglob("*") if p.is_file())
            shutil.rmtree(temp_dir)
            if stale_count:
                logger.info(
                    "setup: removed %d stale file(s) left by a prior run at %s",
                    stale_count,
                    temp_dir,
                )
        temp_dir.mkdir(parents=True)
    except OSError as exc:
        raise RuntimeError(
            f"Could not create temp directory {temp_dir}: {exc}"
        ) from exc
    _initialized = True
    return temp_dir


def cleanup() -> None:
    """Delete the temp stretch directory and all its contents. Never raises."""
    temp_dir = BASE_DIR / TEMP_DIR_NAME
    if not temp_dir.exists():
        return
    try:
        file_count = sum(1 for p in temp_dir.rglob("*") if p.is_file())
        shutil.rmtree(temp_dir)
        logger.info("cleanup: removed %d temp file(s) from %s", file_count, temp_dir)
    except OSError as exc:
        logger.error("cleanup: failed to remove %s: %s", temp_dir, exc)


def get_temp_dir() -> Path:
    """Return the temp stretch directory. Raises RuntimeError if setup() has not been called yet."""
    if not _initialized:
        raise RuntimeError(
            "get_temp_dir() called before setup() — call temp_manager.setup() first"
        )
    return BASE_DIR / TEMP_DIR_NAME
