import pytest

from core.energy_profile import get_targets


class TestSteadyProfile:
    def test_bpm_offset_is_zero_at_start(self):
        assert get_targets("steady", 0.0)["bpm_offset"] == 0

    def test_bpm_offset_is_zero_at_midpoint(self):
        assert get_targets("steady", 0.5)["bpm_offset"] == 0

    def test_bpm_offset_is_zero_at_end(self):
        assert get_targets("steady", 1.0)["bpm_offset"] == 0

    def test_energy_target_is_constant(self):
        assert get_targets("steady", 0.0)["energy_target"] == get_targets("steady", 1.0)["energy_target"]


class TestBuildProfile:
    def test_bpm_offset_lower_at_start_than_end(self):
        assert get_targets("build", 0.0)["bpm_offset"] < get_targets("build", 1.0)["bpm_offset"]

    def test_energy_target_greater_at_end_than_start(self):
        assert get_targets("build", 1.0)["energy_target"] > get_targets("build", 0.0)["energy_target"]


class TestPyramidProfile:
    def test_bpm_offset_peaks_at_midpoint(self):
        mid = get_targets("pyramid", 0.5)["bpm_offset"]
        assert mid > get_targets("pyramid", 0.0)["bpm_offset"]
        assert mid > get_targets("pyramid", 1.0)["bpm_offset"]

    def test_energy_target_peaks_at_midpoint(self):
        mid = get_targets("pyramid", 0.5)["energy_target"]
        assert mid > get_targets("pyramid", 0.0)["energy_target"]
        assert mid > get_targets("pyramid", 1.0)["energy_target"]


class TestValidation:
    def test_unknown_profile_raises_value_error(self):
        with pytest.raises(ValueError, match="sprint"):
            get_targets("sprint", 0.5)

    def test_position_zero_does_not_raise_for_any_profile(self):
        for profile in ("steady", "build", "pyramid"):
            get_targets(profile, 0.0)

    def test_position_one_does_not_raise_for_any_profile(self):
        for profile in ("steady", "build", "pyramid"):
            get_targets(profile, 1.0)
