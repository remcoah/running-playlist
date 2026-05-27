from __future__ import annotations

import random
from datetime import datetime, timezone

from config.settings import COOLDOWN_MINS, RECENTLY_PLAYED_WINDOW_MINS, WARMUP_MINS
from core.run_context import RunContext
from core.playlist_rules import (
    apply_warmup_cooldown,
    exclude_recently_played,
    filter_by_bpm,
)


def build_playlist(context: RunContext, library: list[dict]) -> dict:
    """Filter the library, fill the run duration with shuffled tracks, and return the ordered playlist dict."""
    # Filter to songs that match the target BPM window
    candidates = filter_by_bpm(library, context.target_bpm, context.bpm_tolerance)

    # Drop songs played too recently to keep the playlist fresh
    candidates = exclude_recently_played(candidates, RECENTLY_PLAYED_WINDOW_MINS)

    # Shuffle for variety, then greedily fill the target run duration.
    # If the pool is exhausted before the target is reached, reshuffle and
    # repeat — each pass uses a different order to avoid back-to-back repeats.
    pool = candidates[:]
    random.shuffle(pool)

    target_secs = int(context.duration_mins * 60)
    queue: list[dict] = []
    total = 0
    while total < target_secs and pool:
        for song in pool:
            if total >= target_secs:
                break
            queue.append(song)
            total += song["duration_secs"]
        random.shuffle(pool)
        # Ensure the first song of a repeat pass doesn't immediately follow itself
        if len(pool) > 1 and queue and pool[0]["path"] == queue[-1]["path"]:
            pool[0], pool[1] = pool[1], pool[0]

    # Reorder queue into warmup → main run → cooldown phases
    queue, warmup_count, cooldown_count = apply_warmup_cooldown(queue, WARMUP_MINS, COOLDOWN_MINS)

    return {
        "tracks": queue,
        "target_bpm": context.target_bpm,
        "total_duration_secs": sum(s["duration_secs"] for s in queue),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "warmup_count": warmup_count,
        "cooldown_count": cooldown_count,
    }
