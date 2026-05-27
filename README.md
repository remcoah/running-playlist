# Running Playlist Generator

A CLI tool that builds a running playlist matched to your pace. Given a distance and pace, it picks songs from your music library where the BPM aligns with your target cadence, arranged into warmup, main run, and cooldown phases.

## How it works

- Calculates your target BPM from your pace and stride length (e.g. 5:30 min/km → ~165 BPM)
- Matches songs by direct BPM or half-time (an 82 BPM track still feels right on the beat)
- Assigns low-energy tracks to warmup and cooldown phases automatically
- Avoids songs you've played recently (default: 7-day window)
- Repeats songs if your library is too small to fill the run

## Requirements

- Python 3.9+
- [Anaconda](https://www.anaconda.com/) or `pip`

## Installation

```bash
# Clone the repo
git clone https://github.com/remcoah/running-playlist.git
cd running-playlist

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
python main.py --distance <km> --pace <min/km> [options]
```

**Required arguments:**

| Argument | Description | Example |
|---|---|---|
| `--distance` | Run distance in kilometres | `10` |
| `--pace` | Pace in minutes per kilometre | `5.5` |

**Optional arguments:**

| Argument | Default | Description |
|---|---|---|
| `--folder` | `songs/` | Path to your music folder |
| `--tolerance` | `10` | BPM tolerance around target (wider = more songs eligible) |
| `--format` | `m3u` | Output format: `m3u` or `json` |
| `--output` | `results/playlist` | Output file path (without extension) |
| `--rescan` | off | Delete cached library and re-analyse all files from scratch |

## Examples

10 km run at 5:30 min/km using your own music folder:

```bash
python main.py --distance 10 --pace 5.5 --folder ~/Music
```

Half marathon with a wider BPM window and JSON output:

```bash
python main.py --distance 21.1 --pace 6.0 --tolerance 20 --format json
```

Force a full rescan after adding new songs:

```bash
python main.py --distance 5 --pace 5.0 --rescan
```

The generated playlist is saved to `results/playlist.m3u` (or `.json`) and can be opened directly in VLC or any M3U-compatible player.

## Supported audio formats

`.mp3`, `.flac`, `.wav`, `.m4a`, `.ogg`, `.aiff`

## Personalisation

Edit `config/user_profile.json` to set your stride length (affects BPM calculation):

```json
{
  "name": "",
  "stride_length_m": 2.2,
  "voiceover_enabled": true
}
```

The default stride length of 2.2 m is a reasonable average for most runners. A shorter stride (e.g. 1.8 m) will produce a higher target BPM at the same pace.

## Project structure

```
running-playlist/
├── config/          # Settings and user profile
├── core/            # Run context, playlist logic, rules
├── music/           # Audio analysis and library cache
├── output/          # Playlist and cue sheet writers
├── results/         # Generated playlists (git-ignored)
├── songs/           # Your music folder (git-ignored)
├── tests/           # pytest test suite
└── main.py          # CLI entry point
```

## Running the tests

```bash
python -m pytest tests/ -v
```
