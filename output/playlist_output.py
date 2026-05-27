from __future__ import annotations

import json
from pathlib import Path


def write_m3u(queue_dict: dict, output_path: Path | str) -> None:
    """Write the playlist to an M3U file with absolute paths so media players like VLC can find the tracks."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ["#EXTM3U"]
    for track in queue_dict["tracks"]:
        # Paths in the library are already absolute; resolve() is a safe no-op
        abs_path = str(Path(track["path"]).resolve())
        title = Path(abs_path).stem
        lines.append(f"#EXTINF:{track['duration_secs']},{title}")
        lines.append(abs_path)

    output_path.write_text("\n".join(lines) + "\n")


def write_json(queue_dict: dict, output_path: Path | str) -> None:
    """Write the full playlist dict to a JSON file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(queue_dict, indent=2))


def format_summary(queue_dict: dict) -> str:
    """Return a formatted string listing each track with its phase label, BPM, energy, and duration."""
    tracks = queue_dict["tracks"]
    warmup_count = queue_dict.get("warmup_count", 0)
    cooldown_count = queue_dict.get("cooldown_count", 0)
    cooldown_start_idx = len(tracks) - cooldown_count

    lines = []
    for i, track in enumerate(tracks, start=1):
        idx = i - 1
        if idx < warmup_count:
            label = " [warmup]  "
        elif idx >= cooldown_start_idx:
            label = " [cooldown]"
        else:
            label = "           "

        title = Path(track["path"]).stem
        mins, secs = divmod(track["duration_secs"], 60)
        lines.append(
            f"{i:>3}.{label} {title:<50}  {track['bpm']} BPM  "
            f"energy {track['energy']:.2f}  {mins}:{secs:02d}"
        )

    total_secs = queue_dict["total_duration_secs"]
    total_mins, remaining_secs = divmod(total_secs, 60)
    lines.append(f"\nTotal: {len(tracks)} tracks — {total_mins}:{remaining_secs:02d}")
    return "\n".join(lines)
