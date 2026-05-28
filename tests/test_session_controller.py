import pytest

from config.settings import INITIAL_VOLUME, VOLUME_STEP
from core.session_controller import (
    advance_track,
    apply_command,
    create_session,
    current_track,
    is_complete,
)


def _make_queue_dict(n: int = 3) -> dict:
    return {
        "tracks": [
            {"path": f"/songs/track_{i}.mp3", "bpm": 150, "duration_secs": 240, "energy": 0.5}
            for i in range(n)
        ],
        "target_bpm": 165,
        "profile": "steady",
        "total_duration_secs": n * 240,
        "generated_at": "2026-01-01T00:00:00+00:00",
        "warmup_count": 0,
        "cooldown_count": 0,
    }


class TestCreateSession:
    def test_valid_queue_dict_returns_correct_initial_state(self):
        qd = _make_queue_dict()
        state = create_session(qd, "crossfade")
        assert state.current_index == 0
        assert state.is_paused is False
        assert state.elapsed_mins == 0.0
        assert state.is_complete is False
        assert state.volume == INITIAL_VOLUME
        assert state.transition_style == "crossfade"
        assert state.queue_dict is qd

    def test_empty_tracks_list_raises_value_error(self):
        qd = _make_queue_dict()
        qd["tracks"] = []
        with pytest.raises(ValueError):
            create_session(qd, "crossfade")

    def test_missing_tracks_key_raises_value_error(self):
        with pytest.raises(ValueError):
            create_session({"target_bpm": 165}, "crossfade")


class TestCurrentTrack:
    def test_returns_correct_track_at_index_0(self):
        qd = _make_queue_dict(3)
        state = create_session(qd, "crossfade")
        assert current_track(state) == qd["tracks"][0]

    def test_returns_correct_track_at_index_2(self):
        qd = _make_queue_dict(3)
        state = create_session(qd, "crossfade")
        state.current_index = 2
        assert current_track(state) == qd["tracks"][2]


class TestAdvanceTrack:
    def test_increments_index_correctly(self):
        state = create_session(_make_queue_dict(3), "crossfade")
        advance_track(state)
        assert state.current_index == 1
        assert state.is_complete is False

    def test_sets_is_complete_when_last_track_reached(self):
        state = create_session(_make_queue_dict(2), "crossfade")
        advance_track(state)
        assert state.is_complete is False
        advance_track(state)
        assert state.is_complete is True


class TestApplyCommand:
    def test_pause_sets_is_paused_true(self):
        state = create_session(_make_queue_dict(), "crossfade")
        apply_command(state, "PAUSE")
        assert state.is_paused is True

    def test_resume_sets_is_paused_false(self):
        state = create_session(_make_queue_dict(), "crossfade")
        state.is_paused = True
        apply_command(state, "RESUME")
        assert state.is_paused is False

    def test_skip_advances_track(self):
        state = create_session(_make_queue_dict(3), "crossfade")
        apply_command(state, "SKIP")
        assert state.current_index == 1

    def test_vol_up_increases_volume_by_step(self):
        state = create_session(_make_queue_dict(), "crossfade")
        state.volume = 0.5
        apply_command(state, "VOL_UP")
        assert state.volume == pytest.approx(0.5 + VOLUME_STEP)

    def test_vol_up_does_not_exceed_one(self):
        state = create_session(_make_queue_dict(), "crossfade")
        state.volume = 1.0
        apply_command(state, "VOL_UP")
        assert state.volume == 1.0

    def test_vol_down_decreases_volume_by_step(self):
        state = create_session(_make_queue_dict(), "crossfade")
        state.volume = 0.5
        apply_command(state, "VOL_DOWN")
        assert state.volume == pytest.approx(0.5 - VOLUME_STEP)

    def test_vol_down_does_not_go_below_zero(self):
        state = create_session(_make_queue_dict(), "crossfade")
        state.volume = 0.0
        apply_command(state, "VOL_DOWN")
        assert state.volume == 0.0

    def test_quit_sets_is_complete_true(self):
        state = create_session(_make_queue_dict(), "crossfade")
        apply_command(state, "QUIT")
        assert state.is_complete is True

    def test_unknown_command_leaves_state_unchanged(self):
        state = create_session(_make_queue_dict(), "crossfade")
        before_index = state.current_index
        before_paused = state.is_paused
        before_volume = state.volume
        apply_command(state, "BANANA")
        assert state.current_index == before_index
        assert state.is_paused == before_paused
        assert state.volume == before_volume
        assert state.is_complete is False
