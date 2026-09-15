import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

import music.audio_processor as audio_processor
from config.settings import PROCESSING_TIME_MULTIPLIER
from music.audio_processor import AudioProcessingError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_ffmpeg_convert(monkeypatch):
    mock = MagicMock(return_value=MagicMock(returncode=0))
    monkeypatch.setattr(audio_processor.subprocess, "run", mock)
    return mock


@pytest.fixture
def mock_librosa_load(monkeypatch):
    mock = MagicMock(return_value=(np.zeros(1000), 22050))
    monkeypatch.setattr(audio_processor.librosa, "load", mock)
    return mock


@pytest.fixture
def mock_time_stretch(monkeypatch):
    mock = MagicMock(side_effect=lambda y, rate: y)
    monkeypatch.setattr(audio_processor.librosa.effects, "time_stretch", mock)
    return mock


@pytest.fixture
def mock_sf_write(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr(audio_processor.sf, "write", mock)
    return mock


# ---------------------------------------------------------------------------
# In-bounds stretching
# ---------------------------------------------------------------------------

def test_ratio_within_bounds_triggers_stretch_and_write(
    tmp_path, mock_ffmpeg_convert, mock_librosa_load, mock_time_stretch, mock_sf_write
):
    result = audio_processor.stretch_track(
        source_path="/music/song.mp3",
        original_bpm=140,
        target_bpm=165,
        temp_dir=tmp_path,
    )

    expected_temp_wav = tmp_path / "song_source.wav"
    mock_ffmpeg_convert.assert_called_once()
    mock_librosa_load.assert_called_once_with(str(expected_temp_wav), sr=None, mono=False)
    mock_time_stretch.assert_called_once()
    mock_sf_write.assert_called_once()
    assert result == tmp_path / "song_165bpm.wav"


def test_ffmpeg_conversion_runs_before_librosa_load_and_never_sees_source_path(
    tmp_path, mock_time_stretch, mock_sf_write, monkeypatch
):
    """Regression test for the CoreAudio/audioread crash: librosa.load must never
    be called with the original source_path — only with the ffmpeg-converted WAV,
    and only after ffmpeg has run. If a future refactor removes the WAV
    pre-conversion step, this test fails instead of the process crashing."""
    call_order = []

    def fake_run(*args, **kwargs):
        call_order.append("ffmpeg")
        return MagicMock(returncode=0)

    def fake_load(path, **kwargs):
        call_order.append(("librosa.load", path))
        return (np.zeros(1000), 22050)

    monkeypatch.setattr(audio_processor.subprocess, "run", fake_run)
    monkeypatch.setattr(audio_processor.librosa, "load", fake_load)

    audio_processor.stretch_track(
        source_path="/music/song.mp3",
        original_bpm=140,
        target_bpm=165,
        temp_dir=tmp_path,
    )

    assert call_order[0] == "ffmpeg"
    assert call_order[1][0] == "librosa.load"

    loaded_path = call_order[1][1]
    assert loaded_path != "/music/song.mp3"
    assert loaded_path == str(tmp_path / "song_source.wav")


# ---------------------------------------------------------------------------
# Out-of-bounds ratios — return original, no processing
# ---------------------------------------------------------------------------

def test_ratio_below_min_returns_original_and_skips_load(tmp_path, mock_ffmpeg_convert, mock_librosa_load):
    result = audio_processor.stretch_track(
        source_path="/music/song.mp3",
        original_bpm=200,
        target_bpm=100,
        temp_dir=tmp_path,
    )

    assert result == Path("/music/song.mp3")
    mock_ffmpeg_convert.assert_not_called()
    mock_librosa_load.assert_not_called()


def test_ratio_above_max_returns_original_and_skips_load(tmp_path, mock_ffmpeg_convert, mock_librosa_load):
    result = audio_processor.stretch_track(
        source_path="/music/song.mp3",
        original_bpm=100,
        target_bpm=130,
        temp_dir=tmp_path,
    )

    assert result == Path("/music/song.mp3")
    mock_ffmpeg_convert.assert_not_called()
    mock_librosa_load.assert_not_called()


def test_ratio_near_one_returns_original_and_skips_load(tmp_path, mock_ffmpeg_convert, mock_librosa_load):
    result = audio_processor.stretch_track(
        source_path="/music/song.mp3",
        original_bpm=150,
        target_bpm=151.5,  # ratio == 1.01, under the 0.02 threshold
        temp_dir=tmp_path,
    )

    assert result == Path("/music/song.mp3")
    mock_ffmpeg_convert.assert_not_called()
    mock_librosa_load.assert_not_called()


# ---------------------------------------------------------------------------
# Invalid original_bpm — must not crash on division by zero
# ---------------------------------------------------------------------------

def test_zero_original_bpm_raises_audio_processing_error(tmp_path, mock_ffmpeg_convert, mock_librosa_load):
    with pytest.raises(AudioProcessingError, match="song.mp3"):
        audio_processor.stretch_track(
            source_path="/music/song.mp3",
            original_bpm=0,
            target_bpm=165,
            temp_dir=tmp_path,
        )

    mock_ffmpeg_convert.assert_not_called()
    mock_librosa_load.assert_not_called()


def test_negative_original_bpm_raises_audio_processing_error(tmp_path, mock_ffmpeg_convert, mock_librosa_load):
    with pytest.raises(AudioProcessingError, match="song.mp3"):
        audio_processor.stretch_track(
            source_path="/music/song.mp3",
            original_bpm=-140,
            target_bpm=165,
            temp_dir=tmp_path,
        )

    mock_ffmpeg_convert.assert_not_called()
    mock_librosa_load.assert_not_called()


# ---------------------------------------------------------------------------
# ffmpeg conversion failures
# ---------------------------------------------------------------------------

def test_ffmpeg_not_installed_raises_audio_processing_error(tmp_path, mock_librosa_load, monkeypatch):
    monkeypatch.setattr(
        audio_processor.subprocess, "run", MagicMock(side_effect=FileNotFoundError("no ffmpeg"))
    )

    with pytest.raises(AudioProcessingError, match="ffmpeg"):
        audio_processor.stretch_track(
            source_path="/music/song.mp3",
            original_bpm=140,
            target_bpm=165,
            temp_dir=tmp_path,
        )

    mock_librosa_load.assert_not_called()


def test_ffmpeg_conversion_failure_raises_audio_processing_error(tmp_path, mock_librosa_load, monkeypatch):
    monkeypatch.setattr(
        audio_processor.subprocess,
        "run",
        MagicMock(
            side_effect=subprocess.CalledProcessError(
                returncode=1, cmd=["ffmpeg"], stderr=b"invalid data found"
            )
        ),
    )

    with pytest.raises(AudioProcessingError, match="song.mp3"):
        audio_processor.stretch_track(
            source_path="/music/song.mp3",
            original_bpm=140,
            target_bpm=165,
            temp_dir=tmp_path,
        )

    mock_librosa_load.assert_not_called()


# ---------------------------------------------------------------------------
# Error wrapping
# ---------------------------------------------------------------------------

def test_librosa_load_failure_raises_audio_processing_error(tmp_path, mock_ffmpeg_convert, monkeypatch):
    monkeypatch.setattr(
        audio_processor.librosa, "load", MagicMock(side_effect=RuntimeError("bad file"))
    )

    with pytest.raises(AudioProcessingError, match="song.mp3"):
        audio_processor.stretch_track(
            source_path="/music/song.mp3",
            original_bpm=140,
            target_bpm=165,
            temp_dir=tmp_path,
        )


def test_time_stretch_failure_raises_audio_processing_error(
    tmp_path, mock_ffmpeg_convert, mock_librosa_load, monkeypatch
):
    monkeypatch.setattr(
        audio_processor.librosa.effects,
        "time_stretch",
        MagicMock(side_effect=RuntimeError("stretch blew up")),
    )

    with pytest.raises(AudioProcessingError, match="song.mp3"):
        audio_processor.stretch_track(
            source_path="/music/song.mp3",
            original_bpm=140,
            target_bpm=165,
            temp_dir=tmp_path,
        )


def test_soundfile_write_failure_raises_audio_processing_error(
    tmp_path, mock_ffmpeg_convert, mock_librosa_load, mock_time_stretch, monkeypatch
):
    monkeypatch.setattr(
        audio_processor.sf, "write", MagicMock(side_effect=OSError("disk full"))
    )

    with pytest.raises(AudioProcessingError, match="song.mp3"):
        audio_processor.stretch_track(
            source_path="/music/song.mp3",
            original_bpm=140,
            target_bpm=165,
            temp_dir=tmp_path,
        )


# ---------------------------------------------------------------------------
# Intermediate WAV cleanup
# ---------------------------------------------------------------------------

def test_temp_wav_removed_even_when_stretch_fails(tmp_path, mock_ffmpeg_convert, monkeypatch):
    temp_wav = tmp_path / "song_source.wav"
    temp_wav.write_bytes(b"fake wav data")
    monkeypatch.setattr(
        audio_processor.librosa, "load", MagicMock(side_effect=RuntimeError("bad file"))
    )

    with pytest.raises(AudioProcessingError):
        audio_processor.stretch_track(
            source_path="/music/song.mp3",
            original_bpm=140,
            target_bpm=165,
            temp_dir=tmp_path,
        )

    assert not temp_wav.exists()


# ---------------------------------------------------------------------------
# estimate_processing_time()
# ---------------------------------------------------------------------------

def test_estimate_processing_time_applies_formula_across_tracks():
    tracks = [
        {"duration_secs": 180},
        {"duration_secs": 210},
        {"duration_secs": 95},
    ]
    expected = (180 + 210 + 95) * PROCESSING_TIME_MULTIPLIER
    assert audio_processor.estimate_processing_time(tracks) == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Stereo handling
# ---------------------------------------------------------------------------

def test_stereo_input_is_stretched_per_channel_and_recombined(
    tmp_path, mock_ffmpeg_convert, mock_time_stretch, mock_sf_write, monkeypatch
):
    stereo_y = np.zeros((2, 1000))  # librosa mono=False shape: (channels, samples)
    monkeypatch.setattr(
        audio_processor.librosa, "load", MagicMock(return_value=(stereo_y, 22050))
    )

    audio_processor.stretch_track(
        source_path="/music/song.mp3",
        original_bpm=140,
        target_bpm=165,
        temp_dir=tmp_path,
    )

    # time_stretch only accepts 1D arrays, so it must be called once per channel
    assert mock_time_stretch.call_count == 2
    for call in mock_time_stretch.call_args_list:
        channel_arg = call.args[0] if call.args else call.kwargs["y"]
        assert channel_arg.ndim == 1

    # soundfile expects (samples, channels) — recombined output must be transposed
    written_data = mock_sf_write.call_args.args[1]
    assert written_data.ndim == 2
    assert written_data.shape == (1000, 2)
