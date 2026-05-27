import pytest

from config.settings import BPM_MAX, BPM_MIN, DEFAULT_BPM_TOLERANCE
from core.run_calculator import build_run_context


# ---------------------------------------------------------------------------
# Duration calculation
# ---------------------------------------------------------------------------

def test_ten_km_at_five_thirty_pace_gives_correct_duration():
    ctx = build_run_context(distance_km=10.0, pace_min_per_km=5.5)
    assert ctx.duration_mins == pytest.approx(55.0)


def test_five_km_at_six_min_pace_gives_correct_duration():
    ctx = build_run_context(distance_km=5.0, pace_min_per_km=6.0)
    assert ctx.duration_mins == pytest.approx(30.0)


def test_half_marathon_at_five_min_pace_gives_correct_duration():
    ctx = build_run_context(distance_km=21.1, pace_min_per_km=5.0)
    assert ctx.duration_mins == pytest.approx(105.5)


# ---------------------------------------------------------------------------
# BPM is within valid range
# ---------------------------------------------------------------------------

def test_slow_pace_bpm_within_valid_range():
    ctx = build_run_context(distance_km=10.0, pace_min_per_km=8.0)
    assert BPM_MIN <= ctx.target_bpm <= BPM_MAX


def test_moderate_pace_bpm_within_valid_range():
    ctx = build_run_context(distance_km=10.0, pace_min_per_km=5.5)
    assert BPM_MIN <= ctx.target_bpm <= BPM_MAX


def test_fast_pace_bpm_within_valid_range():
    ctx = build_run_context(distance_km=10.0, pace_min_per_km=4.0)
    assert BPM_MIN <= ctx.target_bpm <= BPM_MAX


# ---------------------------------------------------------------------------
# BPM changes meaningfully with pace
# ---------------------------------------------------------------------------

def test_faster_pace_produces_higher_bpm():
    fast = build_run_context(distance_km=10.0, pace_min_per_km=4.0)
    slow = build_run_context(distance_km=10.0, pace_min_per_km=7.0)
    assert fast.target_bpm > slow.target_bpm


def test_slower_pace_produces_lower_bpm():
    moderate = build_run_context(distance_km=10.0, pace_min_per_km=5.5)
    slow     = build_run_context(distance_km=10.0, pace_min_per_km=7.5)
    assert moderate.target_bpm > slow.target_bpm


# ---------------------------------------------------------------------------
# Fixed fields
# ---------------------------------------------------------------------------

def test_source_is_always_manual():
    ctx = build_run_context(distance_km=10.0, pace_min_per_km=5.5)
    assert ctx.source == "manual"


def test_live_hr_is_always_none():
    ctx = build_run_context(distance_km=10.0, pace_min_per_km=5.5)
    assert ctx.live_hr is None


def test_bpm_tolerance_matches_settings():
    ctx = build_run_context(distance_km=10.0, pace_min_per_km=5.5)
    assert ctx.bpm_tolerance == DEFAULT_BPM_TOLERANCE


# ---------------------------------------------------------------------------
# Edge cases — valid inputs
# ---------------------------------------------------------------------------

def test_very_short_run_returns_valid_context():
    ctx = build_run_context(distance_km=1.0, pace_min_per_km=5.0)
    assert ctx.duration_mins == pytest.approx(5.0)
    assert BPM_MIN <= ctx.target_bpm <= BPM_MAX


def test_marathon_returns_valid_context():
    ctx = build_run_context(distance_km=42.2, pace_min_per_km=6.0)
    assert ctx.duration_mins == pytest.approx(253.2)
    assert BPM_MIN <= ctx.target_bpm <= BPM_MAX


# ---------------------------------------------------------------------------
# Edge cases — invalid inputs
# ---------------------------------------------------------------------------

def test_zero_distance_raises_value_error():
    with pytest.raises(ValueError):
        build_run_context(distance_km=0.0, pace_min_per_km=5.0)


def test_negative_distance_raises_value_error():
    with pytest.raises(ValueError):
        build_run_context(distance_km=-5.0, pace_min_per_km=5.0)


def test_zero_pace_raises_value_error():
    with pytest.raises(ValueError):
        build_run_context(distance_km=10.0, pace_min_per_km=0.0)


def test_negative_pace_raises_value_error():
    with pytest.raises(ValueError):
        build_run_context(distance_km=10.0, pace_min_per_km=-1.0)
