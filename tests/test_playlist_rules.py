from datetime import datetime, timedelta, timezone

import pytest

from config.settings import COOLDOWN_MAX_ENERGY, WARMUP_MAX_ENERGY
from core.playlist_rules import (
    apply_warmup_cooldown,
    exclude_recently_played,
    filter_by_bpm,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_song(path="song.mp3", bpm=160, duration_secs=240, energy=0.8, last_played=None):
    """Return a minimal song dict matching the project schema."""
    return {
        "path": path,
        "bpm": bpm,
        "duration_secs": duration_secs,
        "energy": energy,
        "last_played": last_played,
    }


def ago(minutes: float) -> str:
    """Return an ISO timestamp string for a point in the past."""
    dt = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    return dt.isoformat()


# ---------------------------------------------------------------------------
# filter_by_bpm
# ---------------------------------------------------------------------------

class TestFilterByBpm:
    def test_empty_library_returns_empty(self):
        assert filter_by_bpm([], target_bpm=160, tolerance=10) == []

    def test_exact_match_is_included(self):
        song = make_song(bpm=160)
        assert filter_by_bpm([song], 160, 10) == [song]

    def test_within_tolerance_upper_bound_is_included(self):
        song = make_song(bpm=170)  # 160 + 10
        assert filter_by_bpm([song], 160, 10) == [song]

    def test_within_tolerance_lower_bound_is_included(self):
        song = make_song(bpm=150)  # 160 - 10
        assert filter_by_bpm([song], 160, 10) == [song]

    def test_just_outside_tolerance_is_excluded(self):
        song = make_song(bpm=171)  # 160 + 11
        assert filter_by_bpm([song], 160, 10) == []

    def test_half_time_within_half_tolerance_is_included(self):
        # target=160, half_time=80, half_tolerance=5 → range [75, 85]
        song = make_song(bpm=80)
        assert filter_by_bpm([song], 160, 10) == [song]

    def test_half_time_at_boundary_is_included(self):
        song = make_song(bpm=85)  # 80 + 5
        assert filter_by_bpm([song], 160, 10) == [song]

    def test_half_time_outside_half_tolerance_is_excluded(self):
        song = make_song(bpm=74)  # 80 - 6, outside half_tolerance of 5
        assert filter_by_bpm([song], 160, 10) == []

    def test_mixed_library_filters_correctly(self):
        songs = [
            make_song(path="a.mp3", bpm=160),   # direct match
            make_song(path="b.mp3", bpm=80),    # half-time match
            make_song(path="c.mp3", bpm=200),   # too fast
            make_song(path="d.mp3", bpm=50),    # too slow
        ]
        result = filter_by_bpm(songs, 160, 10)
        paths = [s["path"] for s in result]
        assert "a.mp3" in paths
        assert "b.mp3" in paths
        assert "c.mp3" not in paths
        assert "d.mp3" not in paths


# ---------------------------------------------------------------------------
# exclude_recently_played
# ---------------------------------------------------------------------------

class TestExcludeRecentlyPlayed:
    def test_empty_library_returns_empty(self):
        assert exclude_recently_played([], within_mins=60) == []

    def test_never_played_song_is_always_included(self):
        song = make_song(last_played=None)
        assert exclude_recently_played([song], within_mins=60) == [song]

    def test_played_within_window_is_excluded(self):
        song = make_song(last_played=ago(30))  # 30 min ago, window=60
        assert exclude_recently_played([song], within_mins=60) == []

    def test_played_outside_window_is_included(self):
        song = make_song(last_played=ago(90))  # 90 min ago, window=60
        assert exclude_recently_played([song], within_mins=60) == [song]

    def test_played_exactly_at_boundary_is_included(self):
        # mins_since >= within_mins, so exactly at boundary counts as old enough
        song = make_song(last_played=ago(60))
        result = exclude_recently_played([song], within_mins=60)
        assert result == [song]

    def test_naive_timestamp_treated_as_utc(self):
        # Naive ISO string (no timezone info) should not crash and should be treated as UTC
        naive_ts = datetime.utcnow().replace(microsecond=0).isoformat()  # no tzinfo
        song = make_song(last_played=naive_ts)
        # Played just now, so should be excluded
        result = exclude_recently_played([song], within_mins=60)
        assert result == []

    def test_mix_of_recent_and_old_songs(self):
        songs = [
            make_song(path="old.mp3",    last_played=ago(200)),
            make_song(path="recent.mp3", last_played=ago(10)),
            make_song(path="never.mp3",  last_played=None),
        ]
        result = exclude_recently_played(songs, within_mins=60)
        paths = [s["path"] for s in result]
        assert "old.mp3"    in paths
        assert "never.mp3"  in paths
        assert "recent.mp3" not in paths


# ---------------------------------------------------------------------------
# apply_warmup_cooldown
# ---------------------------------------------------------------------------

class TestApplyWarmupCooldown:
    def test_empty_queue_returns_empty_with_zero_counts(self):
        result, warmup_count, cooldown_count = apply_warmup_cooldown([], 5, 5)
        assert result == []
        assert warmup_count == 0
        assert cooldown_count == 0

    def test_return_type_is_tuple_of_list_and_two_ints(self):
        queue = [make_song()]
        result = apply_warmup_cooldown(queue, 5, 5)
        assert isinstance(result, tuple)
        assert len(result) == 3
        assert isinstance(result[0], list)
        assert isinstance(result[1], int)
        assert isinstance(result[2], int)

    def test_high_energy_songs_go_to_main_not_phases(self):
        # All songs exceed both energy caps → nothing assigned to warmup or cooldown
        songs = [make_song(path=f"{i}.mp3", energy=0.9) for i in range(3)]
        _, warmup_count, cooldown_count = apply_warmup_cooldown(songs, 5, 5)
        assert warmup_count == 0
        assert cooldown_count == 0

    def test_cooldown_gets_calmest_songs(self):
        # Only one song is below COOLDOWN_MAX_ENERGY — it should go to cooldown
        calm   = make_song(path="calm.mp3",   energy=COOLDOWN_MAX_ENERGY - 0.1, duration_secs=300)
        medium = make_song(path="medium.mp3", energy=WARMUP_MAX_ENERGY - 0.01,  duration_secs=300)
        loud   = make_song(path="loud.mp3",   energy=0.9,                       duration_secs=300)

        tracks, warmup_count, cooldown_count = apply_warmup_cooldown(
            [calm, medium, loud], warmup_mins=5, cooldown_mins=5
        )
        assert cooldown_count == 1
        assert tracks[-1]["path"] == "calm.mp3"

    def test_warmup_songs_come_before_main(self):
        # calm goes to cooldown, medium goes to warmup, loud goes to main
        calm   = make_song(path="calm.mp3",   energy=0.3, duration_secs=300)
        medium = make_song(path="medium.mp3", energy=0.55, duration_secs=300)
        loud   = make_song(path="loud.mp3",   energy=0.9, duration_secs=300)

        tracks, warmup_count, cooldown_count = apply_warmup_cooldown(
            [calm, medium, loud], warmup_mins=5, cooldown_mins=5
        )
        assert warmup_count >= 1
        assert tracks[0]["path"] == "medium.mp3"   # warmup is first
        assert tracks[-1]["path"] == "calm.mp3"    # cooldown is last

    def test_order_is_warmup_then_main_then_cooldown(self):
        songs = [
            make_song(path="a.mp3", energy=0.2, duration_secs=300),  # → cooldown
            make_song(path="b.mp3", energy=0.55, duration_secs=300), # → warmup
            make_song(path="c.mp3", energy=0.95, duration_secs=300), # → main
        ]
        tracks, warmup_count, cooldown_count = apply_warmup_cooldown(
            songs, warmup_mins=5, cooldown_mins=5
        )
        assert tracks[0]["path"] == "b.mp3"   # warmup
        assert tracks[1]["path"] == "c.mp3"   # main
        assert tracks[2]["path"] == "a.mp3"   # cooldown

    def test_phase_counts_match_actual_positions(self):
        songs = [
            make_song(path="a.mp3", energy=0.2,  duration_secs=300),
            make_song(path="b.mp3", energy=0.55, duration_secs=300),
            make_song(path="c.mp3", energy=0.95, duration_secs=300),
        ]
        tracks, warmup_count, cooldown_count = apply_warmup_cooldown(
            songs, warmup_mins=5, cooldown_mins=5
        )
        cooldown_start = len(tracks) - cooldown_count
        # First warmup_count tracks should be the lowest-energy non-cooldown songs
        warmup_tracks   = tracks[:warmup_count]
        cooldown_tracks = tracks[cooldown_start:]
        for w in warmup_tracks:
            assert w["energy"] <= WARMUP_MAX_ENERGY
        for c in cooldown_tracks:
            assert c["energy"] <= COOLDOWN_MAX_ENERGY

    def test_duration_budget_limits_phase_size(self):
        # Three calm songs but warmup budget only covers one (300s = 5 min)
        songs = [
            make_song(path=f"{i}.mp3", energy=0.4, duration_secs=300)
            for i in range(4)
        ]
        _, warmup_count, cooldown_count = apply_warmup_cooldown(
            songs, warmup_mins=5, cooldown_mins=5
        )
        # Budget is 300s each; each song is 300s — so at most 1 song per phase
        assert warmup_count <= 1
        assert cooldown_count <= 1

    def test_total_track_count_unchanged(self):
        songs = [make_song(path=f"{i}.mp3", energy=i * 0.1) for i in range(6)]
        tracks, _, _ = apply_warmup_cooldown(songs, warmup_mins=5, cooldown_mins=5)
        assert len(tracks) == len(songs)
