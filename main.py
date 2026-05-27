import argparse
import sys
from pathlib import Path

import config.settings as settings
from config.user_profile import load_profile
from core.error_handler import configure_logging, safe_call
from core.run_calculator import build_run_context
from music.audio_analyzer import get_library, mark_played, scan_folder
from core.playlist_builder import build_playlist
from output.playlist_output import format_summary, write_json, write_m3u
from output.cue_library import build_cues, write_cue_file


def _parse_args() -> argparse.Namespace:
    """Define and parse CLI arguments, returning the populated namespace."""
    parser = argparse.ArgumentParser(description="Generate a running playlist.")
    parser.add_argument("--distance", type=float, required=True,  help="Distance in km")
    parser.add_argument("--pace",     type=float, required=True,  help="Pace in min/km")
    parser.add_argument(
        "--folder",
        type=str,
        default=str(settings.DEFAULT_MUSIC_FOLDER),
        help="Path to music folder (default: %(default)s)",
    )
    parser.add_argument(
        "--tolerance",
        type=int,
        default=settings.DEFAULT_BPM_TOLERANCE,
        help="BPM tolerance around target (default: %(default)s)",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["m3u", "json"],
        default=settings.DEFAULT_OUTPUT_FORMAT,
        help="Output format (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=settings.DEFAULT_OUTPUT_PATH,
        help="Output file path without extension (default: %(default)s)",
    )
    parser.add_argument(
        "--rescan",
        action="store_true",
        help="Delete song_library.json and rebuild from scratch before generating playlist",
    )
    return parser.parse_args()


def main() -> None:
    """Orchestrate the full pipeline: parse args, build run context, scan library, generate playlist, and write output."""
    configure_logging()
    args = _parse_args()

    # Step 1: optionally wipe the library cache before scanning
    if args.rescan and settings.SONG_LIBRARY_PATH.exists():
        settings.SONG_LIBRARY_PATH.unlink()
        print("Library cache cleared — rescanning from scratch")

    # Step 2: build run context from distance + pace + user profile
    profile = load_profile()
    context = safe_call(
        build_run_context,
        args.distance,
        args.pace,
        args.tolerance,
        profile.get("stride_length_m", settings.DEFAULT_STRIDE_LENGTH_M),
        fallback=None,
        label="build_run_context",
    )
    if context is None:
        print("Error: could not calculate run context. Check --distance and --pace.")
        sys.exit(1)

    print(f"Run: {args.distance} km at {args.pace} min/km → "
          f"{context.duration_mins:.1f} min, target {context.target_bpm} BPM")

    # Step 3: scan music folder — fatal if the folder is missing or empty
    try:
        scan_folder(args.folder)
    except FileNotFoundError:
        print(f"Error: music folder not found: {args.folder}")
        print("Check the path and try again.")
        sys.exit(1)
    except ValueError:
        exts = " ".join(sorted({".mp3", ".flac", ".wav", ".m4a"}))
        print(f"Error: no supported audio files found in {args.folder}")
        print(f"Supported formats: {exts}")
        sys.exit(1)

    library = safe_call(get_library, fallback=[], label="get_library")
    if not library:
        print("Error: library is empty after scan. Check --folder and re-run.")
        sys.exit(1)

    print(f"Library: {len(library)} tracks scanned")

    # Step 4: build the playlist
    playlist = safe_call(
        build_playlist,
        context,
        library,
        fallback=None,
        label="build_playlist",
    )
    if not playlist or not playlist.get("tracks"):
        print("Error: could not build a playlist. Try widening BPM tolerance or adding more songs.")
        sys.exit(1)

    track_count = len(playlist["tracks"])
    total_mins = playlist["total_duration_secs"] // 60
    print(f"Playlist: {track_count} tracks, {total_mins} min total")

    # Step 5: write output file
    base_output = Path(args.output)
    output_path = base_output.parent / (base_output.name + f".{args.format}")
    if args.format == "m3u":
        safe_call(write_m3u, playlist, output_path, fallback=None, label="write_m3u")
    else:
        safe_call(write_json, playlist, output_path, fallback=None, label="write_json")

    played_paths = [track["path"] for track in playlist["tracks"]]
    safe_call(mark_played, played_paths, fallback=None, label="mark_played")

    print(format_summary(playlist))

    # Step 6: write cue sheet alongside the playlist
    cues = safe_call(build_cues, playlist, fallback=[], label="build_cues")
    if cues:
        cue_path = base_output.parent / (base_output.name + ".cue.json")
        safe_call(write_cue_file, cues, cue_path, fallback=None, label="write_cue_file")

    print(f"Saved → {output_path}")


if __name__ == "__main__":
    main()
