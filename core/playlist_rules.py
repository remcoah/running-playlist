from __future__ import annotations

from datetime import datetime, timezone

from config.settings import COOLDOWN_MAX_ENERGY, WARMUP_MAX_ENERGY


def filter_by_bpm(songs: list[dict], target_bpm: int, tolerance: int) -> list[dict]:
    """Return songs whose BPM matches the target directly or at half-time (target / 2)."""
    # Accept songs at the target BPM or at half-time (target/2), because a song
    # at half the cadence still feels natural — every other beat hits a footstrike.
    half_time = target_bpm / 2
    return [
        s for s in songs
        if abs(s["bpm"] - target_bpm) <= tolerance
        or abs(s["bpm"] - half_time) <= tolerance / 2
    ]


def exclude_recently_played(songs: list[dict], within_mins: int) -> list[dict]:
    """Remove songs that were played within the given number of minutes."""
    now = datetime.now(timezone.utc)
    result = []
    for song in songs:
        last = song.get("last_played")
        if last is None:
            # Never played — always include
            result.append(song)
            continue
        played_at = datetime.fromisoformat(last)
        # Treat naive timestamps as UTC
        if played_at.tzinfo is None:
            played_at = played_at.replace(tzinfo=timezone.utc)
        mins_since = (now - played_at).total_seconds() / 60
        if mins_since >= within_mins:
            result.append(song)
    return result


def apply_warmup_cooldown(
    queue: list[dict], warmup_mins: int, cooldown_mins: int
) -> tuple[list[dict], int, int]:
    """Reorder the queue into warmup → main run → cooldown phases based on energy, returning the ordered list and phase counts."""
    # Sort ascending by energy so the calmest songs surface first
    by_energy = sorted(queue, key=lambda s: s["energy"])
    used: set[str] = set()

    def _fill_phase(budget_secs: int, max_energy: float) -> list[dict]:
        """Greedily pick the calmest unused songs up to the time budget and energy cap."""
        phase: list[dict] = []
        total = 0
        for song in by_energy:
            if song["path"] in used:
                continue
            if song["energy"] > max_energy:
                break  # list is sorted, no point continuing
            if total >= budget_secs:
                break
            phase.append(song)
            used.add(song["path"])
            total += song["duration_secs"]
        return phase

    # Cooldown gets first pick of the calmest songs (stricter energy cap)
    cooldown = _fill_phase(cooldown_mins * 60, COOLDOWN_MAX_ENERGY)
    # Warmup picks from what remains (slightly looser energy cap)
    warmup = _fill_phase(warmup_mins * 60, WARMUP_MAX_ENERGY)

    main = [s for s in queue if s["path"] not in used]

    # Return counts so callers can record exact phase boundaries
    return warmup + main + cooldown, len(warmup), len(cooldown)
