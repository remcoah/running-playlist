import pytest

import core.playlist_builder as playlist_builder
from config.settings import DEFAULT_BPM_TOLERANCE
from core.playlist_builder import build_playlist
from core.run_context import RunContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
