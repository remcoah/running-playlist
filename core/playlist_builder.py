from __future__ import annotations

import logging
from datetime import datetime, timezone

from config.settings import (
    COOLDOWN_MINS,
    DEFAULT_ENERGY_PROFILE,
    RECENTLY_PLAYED_WINDOW_MINS,
    SLOT_DURATION_MINS,
    WARMUP_MINS,
)
from core.energy_profile import get_targets
from core.playlist_rules import (
    apply_warmup_cooldown,
    exclude_recently_played,
    filter_by_bpm,
    get_repeat_candidates,
)
from core.run_context import RunContext

logger = logging.getLogger("running_playlist")


def _pick_song(
    candidates: list[dict],
    slot_bpm: int,
    slot_energy: float,
    tolerance: int,
    used_paths: list[str],
) -> dict:
    """Pick the candidate that best matches the slot BPM and energy target.

    Fallback order:
      1. Unused tracks at strict BPM tolerance
      2. Unused tracks at doubled BPM tolerance
      3. Repeat candidates spaced >= REPEAT_ALLOWED_AFTER slots
      4. Raise ValueError if nothing qualifies
    """
    used_set = set(used_paths)
    unused = [s for s in candidates if s["path"] not in used_set]

    eligible = filter_by_bpm(unused, slot_bpm, tolerance)

    if not eligible:
        logger.warning(
            "No unused tracks for BPM %d ± %d. Widening search to ± %d.",
            slot_bpm, tolerance, tolerance * 2,
        )
        eligible = filter_by_bpm(unused, slot_bpm, tolerance * 2)

    if not eligible:
        eligible = get_repeat_candidates(candidates, used_paths, slot_bpm, tolerance * 2)

    if not eligible:
        raise ValueError(
            f"Library has no tracks near {slot_bpm} BPM even with "
            f"doubled tolerance. Add more songs or adjust your pace."
        )

    last = used_paths[-1] if used_paths else None
    pool = [s for s in eligible if s["path"] != last] or eligible

    return min(pool, key=lambda s: abs(s["energy"] - slot_energy))


def build_playlist(
    context: RunContext,
    library: list[dict],
    profile: str = DEFAULT_ENERGY_PROFILE,
) -> dict:
    """Build a segment-aware playlist, picking one song per time slot to match the profile's BPM and energy targets."""
    candidates = exclude_recently_played(library, RECENTLY_PLAYED_WINDOW_MINS)

    total_slots = max(1, round(context.duration_mins / SLOT_DURATION_MINS))
    used_paths: list[str] = []
    tracks: list[dict] = []

    for slot_idx in range(total_slots):
        position = slot_idx / max(total_slots - 1, 1)
        targets = get_targets(profile, position)
        slot_bpm = context.target_bpm + targets["bpm_offset"]

        song = _pick_song(
            candidates, slot_bpm, targets["energy_target"],
            context.bpm_tolerance, used_paths,
        )
        tracks.append(song)
        used_paths.append(song["path"])

    tracks, warmup_count, cooldown_count = apply_warmup_cooldown(tracks, WARMUP_MINS, COOLDOWN_MINS)

    return {
        "tracks": tracks,
        "target_bpm": context.target_bpm,
        "profile": profile,
        "total_duration_secs": sum(s["duration_secs"] for s in tracks),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "warmup_count": warmup_count,
        "cooldown_count": cooldown_count,
    }
