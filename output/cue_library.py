from __future__ import annotations

import json
from pathlib import Path


def build_cues(queue_dict: dict) -> list[dict]:
    """Build a list of time-stamped phase markers (WARMUP, MAIN_RUN, COOLDOWN) from the playlist."""
    tracks = queue_dict["tracks"]
    warmup_count = queue_dict.get("warmup_count", 0)
    cooldown_count = queue_dict.get("cooldown_count", 0)
    cooldown_start_idx = len(tracks) - cooldown_count

    cues: list[dict] = []
    offset = 0
    current_phase = None

    for idx, track in enumerate(tracks):
        if idx < warmup_count:
            phase = "WARMUP"
        elif idx >= cooldown_start_idx:
            phase = "COOLDOWN"
        else:
            phase = "MAIN_RUN"

        # Emit a cue only when the phase changes
        if phase != current_phase:
            cues.append({"label": phase, "offset_secs": offset})
            current_phase = phase

        offset += track["duration_secs"]

    return cues


def write_cue_file(cues: list[dict], output_path: Path | str) -> None:
    """Write the cue sheet to a JSON file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(cues, indent=2))
