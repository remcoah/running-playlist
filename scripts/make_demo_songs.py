"""Generate short synthetic drum-loop WAV tracks so the app can be tried without a music library."""

import argparse
from pathlib import Path

import numpy as np
import soundfile as sf

SAMPLE_RATE = 22050
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "songs"

# (bpm, duration_secs, gain) — gains vary so energy normalisation has a spread
TRACKS = [
    (145, 235, 0.25),
    (150, 240, 0.40),
    (155, 250, 0.55),
    (160, 230, 0.85),
    (165, 245, 0.70),
    (168, 235, 0.35),
    (172, 250, 0.95),
    (175, 240, 0.50),
]


def _kick(rng: np.random.Generator) -> np.ndarray:
    """Return a short pitch-dropping sine kick with a transient click."""
    t = np.arange(int(0.25 * SAMPLE_RATE)) / SAMPLE_RATE
    freq = 50 + 100 * np.exp(-t * 30)
    body = np.sin(2 * np.pi * np.cumsum(freq) / SAMPLE_RATE) * np.exp(-t * 12)
    click = rng.standard_normal(len(t)) * np.exp(-t * 400) * 0.3
    return body + click


def _snare(rng: np.random.Generator) -> np.ndarray:
    """Return a noise burst with a tonal body, used on beats 2 and 4."""
    t = np.arange(int(0.2 * SAMPLE_RATE)) / SAMPLE_RATE
    noise = rng.standard_normal(len(t)) * np.exp(-t * 25)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30)
    return 0.6 * noise + 0.4 * tone


def _hat(rng: np.random.Generator) -> np.ndarray:
    """Return a very short high-passed noise tick for off-beat hi-hats."""
    n = int(0.05 * SAMPLE_RATE)
    noise = rng.standard_normal(n)
    noise = np.diff(noise, prepend=0.0)  # crude high-pass
    return noise * np.exp(-np.arange(n) / SAMPLE_RATE * 120) * 0.25


def _place(buf: np.ndarray, sample: np.ndarray, start: int) -> None:
    """Mix a one-shot sample into buf at the given offset, truncating at the end."""
    end = min(start + len(sample), len(buf))
    buf[start:end] += sample[: end - start]


def make_track(bpm: int, duration_secs: int, gain: float, seed: int) -> np.ndarray:
    """Render a four-on-the-floor drum loop at the given tempo, length and level."""
    rng = np.random.default_rng(seed)
    buf = np.zeros(int(duration_secs * SAMPLE_RATE))
    beat_len = 60.0 / bpm * SAMPLE_RATE
    kick, snare, hat = _kick(rng), _snare(rng), _hat(rng)

    n_beats = int(len(buf) / beat_len)
    for i in range(n_beats):
        start = int(i * beat_len)
        _place(buf, kick, start)
        if i % 4 in (1, 3):
            _place(buf, snare, start)
        _place(buf, hat, int(start + beat_len / 2))

    buf /= np.max(np.abs(buf)) or 1.0
    return (buf * gain).astype(np.float32)


def main() -> None:
    """Write the demo tracks to the output folder."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Folder to write WAV files into (default: %(default)s)",
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    for i, (bpm, duration_secs, gain) in enumerate(TRACKS, start=1):
        path = args.out / f"demo_{i:02d}_{bpm}bpm.wav"
        sf.write(path, make_track(bpm, duration_secs, gain, seed=i), SAMPLE_RATE)
        print(f"Wrote {path} ({duration_secs}s, gain {gain})")

    print(f"\nDone. Try: python main.py --distance 2 --pace 5.5 --folder {args.out}")


if __name__ == "__main__":
    main()
