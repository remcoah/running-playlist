"""Tests for music.audio_analyzer: library filtering by scanned folder."""

import json

import music.audio_analyzer as audio_analyzer


def _song(path, energy):
    return {
        "path": str(path),
        "bpm": 165,
        "duration_secs": 240,
        "energy": energy,
        "last_played": None,
    }


def test_get_library_only_returns_songs_inside_the_scanned_folder(
    tmp_path, monkeypatch
):
    # "songs2" shares a string prefix with "songs" — a naive startswith check
    # would wrongly include it
    run_folder = tmp_path / "songs"
    other_folder = tmp_path / "songs2"
    cache = [
        _song(run_folder / "a.mp3", 0.02),
        _song(run_folder / "sub" / "b.mp3", 0.04),
        _song(other_folder / "c.mp3", 0.08),
    ]
    library_path = tmp_path / "song_library.json"
    library_path.write_text(json.dumps(cache))
    monkeypatch.setattr(audio_analyzer, "SONG_LIBRARY_PATH", library_path)

    library = audio_analyzer.get_library(str(run_folder))

    assert sorted(s["path"] for s in library) == [
        str(run_folder / "a.mp3"),
        str(run_folder / "sub" / "b.mp3"),
    ]
