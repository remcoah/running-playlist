"""Tests for output.playlist_output: format_summary's BPM-arrow display logic."""

from output.playlist_output import format_summary

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _queue(tracks, warmup_count=0, cooldown_count=0):
    return {
        "tracks": tracks,
        "warmup_count": warmup_count,
        "cooldown_count": cooldown_count,
        "total_duration_secs": sum(t["duration_secs"] for t in tracks),
    }


# ---------------------------------------------------------------------------
# format_summary() — BPM display
# ---------------------------------------------------------------------------


def test_track_without_target_bpm_formats_as_before():
    track = {
        "path": "/music/Song One.mp3",
        "duration_secs": 263,
        "bpm": 165,
        "energy": 0.72,
    }
    result = format_summary(_queue([track]))
    assert "165 BPM" in result
    assert "→" not in result


def test_track_with_target_bpm_within_one_formats_without_arrow():
    track = {
        "path": "/music/Song One.mp3",
        "duration_secs": 263,
        "bpm": 165,
        "original_bpm": 165,
        "target_bpm": 165.6,  # diff of 0.6 — within the rounding tolerance
        "energy": 0.72,
    }
    result = format_summary(_queue([track]))
    assert "165 BPM" in result
    assert "→" not in result


def test_track_with_target_bpm_differing_by_more_than_one_shows_arrow():
    track = {
        "path": "/music/Song One.mp3",
        "duration_secs": 263,
        "bpm": 144,
        "original_bpm": 144,
        "target_bpm": 165,
        "energy": 0.72,
    }
    result = format_summary(_queue([track]))
    assert "144→165 BPM" in result


def test_existing_summary_line_format_is_unchanged_for_non_stretched_track():
    track = {
        "path": "/music/Song One.mp3",
        "duration_secs": 263,
        "bpm": 165,
        "energy": 0.72,
    }
    result = format_summary(_queue([track]))
    lines = result.split("\n")
    assert (
        lines[0]
        == "  1.            Song One                                            165 BPM  energy 0.72  4:23"
    )
    assert lines[-1] == "Total: 1 tracks — 4:23"
