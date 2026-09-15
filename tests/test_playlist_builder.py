"""Tests for core.playlist_builder: slot_target_bpm wiring and BPM-proximity selection."""

import pytest

import core.playlist_builder as playlist_builder
from config.settings import DEFAULT_BPM_TOLERANCE
from core.playlist_builder import _pick_song, build_playlist
from core.run_context import RunContext

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _song(path, bpm, energy, duration_secs=200):
    return {
        "path": path,
        "bpm": bpm,
        "duration_secs": duration_secs,
        "energy": energy,
        "last_played": None,
    }


def _make_library(n=20, bpm_start=140, bpm_step=3):
    """A synthetic library spanning a wide, densely-spaced BPM range.

    energy is fixed at 0.9 for every song — above both WARMUP_MAX_ENERGY and
    COOLDOWN_MAX_ENERGY, so apply_warmup_cooldown never pulls any track into a
    warmup/cooldown phase and the returned tracks list stays in raw slot order.
    That makes positional assertions (first/midpoint/last slot) meaningful.
    """
    return [
        {
            "path": f"/music/song{i}.mp3",
            "bpm": bpm_start + i * bpm_step,
            "duration_secs": 200,
            "energy": 0.9,
            "last_played": None,
        }
        for i in range(n)
    ]


def _make_context(duration_mins, target_bpm=165, tolerance=DEFAULT_BPM_TOLERANCE):
    return RunContext(
        duration_mins=duration_mins,
        target_bpm=target_bpm,
        bpm_tolerance=tolerance,
        source="manual",
        live_hr=None,
    )


# ---------------------------------------------------------------------------
# slot_target_bpm is attached to every track, for every profile
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("profile", ["steady", "build", "pyramid"])
def test_slot_target_bpm_attached_to_every_track(profile):
    context = _make_context(duration_mins=20)  # 5 slots
    playlist = build_playlist(context, _make_library(), profile, ignore_recent=True)

    assert len(playlist["tracks"]) == 5
    assert all("slot_target_bpm" in t for t in playlist["tracks"])


# ---------------------------------------------------------------------------
# steady profile: flat target across every slot
# ---------------------------------------------------------------------------


def test_steady_profile_slot_target_bpm_equals_context_target_bpm():
    context = _make_context(duration_mins=20)  # 5 slots
    playlist = build_playlist(context, _make_library(), "steady", ignore_recent=True)

    values = {t["slot_target_bpm"] for t in playlist["tracks"]}
    assert values == {context.target_bpm}


# ---------------------------------------------------------------------------
# pyramid profile: midpoint slot is the peak, not the edges
# ---------------------------------------------------------------------------


def test_pyramid_profile_midpoint_slot_target_bpm_higher_than_edges():
    context = _make_context(duration_mins=20)  # 5 slots -> positions 0, .25, .5, .75, 1
    playlist = build_playlist(context, _make_library(), "pyramid", ignore_recent=True)

    tracks = playlist["tracks"]
    first, midpoint, last = tracks[0], tracks[len(tracks) // 2], tracks[-1]

    assert midpoint["slot_target_bpm"] > first["slot_target_bpm"]
    assert midpoint["slot_target_bpm"] > last["slot_target_bpm"]


# ---------------------------------------------------------------------------
# Repeated song across slots: independent track dicts, not shared references
# ---------------------------------------------------------------------------


def test_repeated_song_produces_independent_track_dicts(monkeypatch):
    shared_song = {
        "path": "/music/only_song.mp3",
        "bpm": 165,
        "duration_secs": 200,
        "energy": 0.9,
        "last_played": None,
    }
    # Force every slot to select the exact same underlying dict object, the
    # way get_repeat_candidates can when the library is too small — without
    # depending on real BPM-tolerance arithmetic to force a repeat.
    monkeypatch.setattr(playlist_builder, "_pick_song", lambda *a, **kw: shared_song)

    context = _make_context(duration_mins=12)  # 3 slots -> positions 0, .5, 1
    playlist = build_playlist(context, [shared_song], "pyramid", ignore_recent=True)

    tracks = playlist["tracks"]
    assert len(tracks) == 3

    # Same path, but genuinely different objects
    assert tracks[0] is not tracks[1]
    assert tracks[1] is not tracks[2]
    assert tracks[0]["path"] == tracks[1]["path"] == tracks[2]["path"]

    # Pyramid at 3 slots: edges (-5) vs midpoint peak (+10) differ
    assert tracks[0]["slot_target_bpm"] != tracks[1]["slot_target_bpm"]

    # Mutating one slot's track must not leak into another's
    tracks[0]["slot_target_bpm"] = 999
    tracks[0]["target_bpm"] = 999
    assert tracks[1]["slot_target_bpm"] != 999
    assert "target_bpm" not in tracks[1]


# ---------------------------------------------------------------------------
# _pick_song: BPM proximity is shortlisted before energy is considered
# ---------------------------------------------------------------------------


class TestPickSongBpmProximity:
    def test_bpm_closest_candidate_wins_over_energy_closest_but_farther_in_bpm(self):
        # With >_BPM_PROXIMITY_SHORTLIST_SIZE candidates eligible, the single
        # best energy match in the whole pool must lose if its BPM distance
        # pushes it out of the shortlist entirely.
        slot_bpm = 165
        slot_energy = 0.5

        bpm_close = _song(
            "bpm_close.mp3", bpm=165, energy=0.95
        )  # distance 0, mediocre energy
        decoy_1 = _song("decoy1.mp3", bpm=166, energy=0.99)  # distance 1
        decoy_2 = _song("decoy2.mp3", bpm=164, energy=0.99)  # distance 1
        energy_close_bpm_far = _song(
            "energy_close.mp3", bpm=155, energy=0.50
        )  # distance 10, exact energy

        winner = _pick_song(
            [bpm_close, decoy_1, decoy_2, energy_close_bpm_far],
            slot_bpm,
            slot_energy,
            tolerance=15,
            used_paths=[],
        )

        assert winner["path"] == "bpm_close.mp3"
        assert winner["path"] != "energy_close.mp3"

    def test_shortlist_excludes_candidates_beyond_the_proximity_window(self):
        slot_bpm = 165
        slot_energy = 0.5

        near_1 = _song("near1.mp3", bpm=166, energy=0.10)  # distance 1
        near_2 = _song(
            "near2.mp3", bpm=163, energy=0.20
        )  # distance 2, best energy match within top 3
        near_3 = _song("near3.mp3", bpm=170, energy=0.05)  # distance 5
        far_perfect_energy = _song(
            "far.mp3", bpm=178, energy=0.50
        )  # distance 13 -> 4th closest, excluded

        winner = _pick_song(
            [far_perfect_energy, near_1, near_2, near_3],
            slot_bpm,
            slot_energy,
            tolerance=15,
            used_paths=[],
        )

        # far.mp3 has the best energy match of all four, but its BPM distance
        # (13) puts it 4th — outside the top-3 shortlist — so it must lose
        # even though nothing in the shortlist matches energy as well.
        assert winner["path"] == "near2.mp3"
        assert winner["path"] != "far.mp3"

    def test_fewer_than_shortlist_size_eligible_uses_all_of_them(self):
        # Only 2 candidates total, well under the shortlist size of 3 — the
        # slice degrades to "use everything eligible" with no special-casing.
        slot_bpm = 165
        slot_energy = 0.5

        a = _song("a.mp3", bpm=170, energy=0.10)
        b = _song("b.mp3", bpm=160, energy=0.50)

        winner = _pick_song([a, b], slot_bpm, slot_energy, tolerance=15, used_paths=[])

        assert winner["path"] == "b.mp3"

    def test_half_time_match_is_sorted_by_half_time_distance_not_raw_distance(self):
        # slot_bpm=160 -> half_time=80. This song only matches via half-time
        # (raw distance to 160 is 79, far outside tolerance) but is a near-
        # perfect half-time match (distance to 80 is 1).
        slot_bpm = 160
        slot_energy = 0.5

        half_time_perfect = _song(
            "ht_perfect.mp3", bpm=81, energy=0.50
        )  # half-time distance 1, exact energy
        direct_a = _song("direct_a.mp3", bpm=168, energy=0.10)  # direct distance 8
        direct_b = _song("direct_b.mp3", bpm=152, energy=0.90)  # direct distance 8
        direct_c = _song(
            "direct_c.mp3", bpm=170, energy=0.20
        )  # direct distance 10 -> should be excluded

        winner = _pick_song(
            [half_time_perfect, direct_a, direct_b, direct_c],
            slot_bpm,
            slot_energy,
            tolerance=10,
            used_paths=[],
        )

        # If half-time distance were computed against the raw slot_bpm (79)
        # instead of slot_bpm / 2 (1), this track would rank last and lose
        # its shortlist spot to direct_c despite having by far the best
        # energy match of all four candidates.
        assert winner["path"] == "ht_perfect.mp3"
        assert winner["half_time_match"] is True
