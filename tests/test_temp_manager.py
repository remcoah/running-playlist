"""Tests for music.temp_manager: temp directory setup, stale-content clearing, cleanup."""

import pytest

import music.temp_manager as temp_manager

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_temp_dir(tmp_path, monkeypatch):
    """Point temp_manager at a throwaway directory and reset its init flag for every test."""
    monkeypatch.setattr(temp_manager, "BASE_DIR", tmp_path)
    monkeypatch.setattr(temp_manager, "TEMP_DIR_NAME", "temp/stretch")
    monkeypatch.setattr(temp_manager, "_initialized", False)
    return tmp_path / "temp" / "stretch"


# ---------------------------------------------------------------------------
# setup()
# ---------------------------------------------------------------------------


def test_setup_creates_temp_directory(isolated_temp_dir):
    temp_manager.setup()
    assert isolated_temp_dir.is_dir()


def test_setup_returns_correct_path(isolated_temp_dir):
    result = temp_manager.setup()
    assert result == isolated_temp_dir


def test_setup_clears_stale_content_from_a_prior_ungraceful_exit(isolated_temp_dir):
    isolated_temp_dir.mkdir(parents=True)
    (isolated_temp_dir / "leftover_165bpm.wav").write_text(
        "orphaned from a crashed run"
    )

    temp_manager.setup()

    assert isolated_temp_dir.is_dir()
    assert list(isolated_temp_dir.iterdir()) == []


# ---------------------------------------------------------------------------
# cleanup()
# ---------------------------------------------------------------------------


def test_cleanup_removes_directory_and_files(isolated_temp_dir):
    temp_manager.setup()
    (isolated_temp_dir / "track1_165bpm.wav").write_text("fake audio")
    (isolated_temp_dir / "track2_165bpm.wav").write_text("fake audio")

    temp_manager.cleanup()

    assert not isolated_temp_dir.exists()


def test_cleanup_does_not_raise_if_directory_missing(isolated_temp_dir):
    assert not isolated_temp_dir.exists()
    temp_manager.cleanup()  # should not raise


# ---------------------------------------------------------------------------
# get_temp_dir()
# ---------------------------------------------------------------------------


def test_get_temp_dir_raises_before_setup():
    with pytest.raises(RuntimeError):
        temp_manager.get_temp_dir()


def test_get_temp_dir_returns_correct_path_after_setup(isolated_temp_dir):
    temp_manager.setup()
    assert temp_manager.get_temp_dir() == isolated_temp_dir
