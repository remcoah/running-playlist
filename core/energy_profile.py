from __future__ import annotations

_PROFILES = {"steady", "build", "pyramid"}


def get_targets(profile: str, position: float) -> dict:
    """Return BPM offset and energy target for a given position on the named profile.

    position: 0.0 = start of run, 1.0 = end of run
    returns: {"bpm_offset": int, "energy_target": float}
    Raises ValueError for unknown profile names.
    """
    if profile not in _PROFILES:
        raise ValueError(
            f"Unknown energy profile '{profile}'. Valid options: {sorted(_PROFILES)}"
        )

    position = max(0.0, min(1.0, position))

    if profile == "steady":
        return {"bpm_offset": 0, "energy_target": 0.6}

    if profile == "build":
        # bpm_offset: -10 at start → +10 at end
        # energy_target: 0.4 at start → 0.9 at end
        bpm_offset = int(round(-10 + 20 * position))
        energy_target = round(0.4 + 0.5 * position, 3)
        return {"bpm_offset": bpm_offset, "energy_target": energy_target}

    # pyramid: ramp up to midpoint, mirror back down
    # intensity: 0.0 at edges → 1.0 at centre
    intensity = 1.0 - 2.0 * abs(position - 0.5)
    bpm_offset = int(round(-5 + 15 * intensity))   # -5 at edges → +10 at peak
    energy_target = round(0.4 + 0.5 * intensity, 3)  # 0.4 at edges → 0.9 at peak
    return {"bpm_offset": bpm_offset, "energy_target": energy_target}
