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
- [pygame](https://www.pygame.org/) (installed via requirements.txt) — required for audio playback. Not needed for `--no-playback` mode.

## Installation

```bash
# Clone the repo
git clone https://github.com/remcoah/running-playlist.git
cd running-playlist

# Install dependencies
pip install -r requirements.txt
# Add your music files to the songs/ folder (MP3, FLAC, WAV, M4A)
```

## Usage

> **Note:** Playlist quality depends on having songs near your 
> target BPM in your library. 

```bash
python main.py --distance <km> --pace <min/km> [options]
```

**Required arguments:**

| Argument | Description | Example |
|---|---|---|
| `--distance` | Run distance in kilometres | `10` |
| `--pace` | Pace in minutes per kilometre | `5.5` |

You will be prompted for: 
  - Transition style (crossfade or hard cut)
  - Energy profile (steady, build, pyramid)

**Optional arguments:**

| Argument | Default | Description |
|---|---|---|
| `--folder` | `songs/` | Path to your music folder |
| `--tolerance` | `15` | BPM tolerance around target (wider = more songs eligible) |
| `--format` | `m3u` | Output format: `m3u` or `json` |
| `--output` | `results/playlist` | Output file path (without extension) |
| `--rescan` | off | Delete cached library and re-analyse all files from scratch |
| `--no-playback` | off | Generate and save the playlist without playing audio |
| `--ignore-recent` | off | Includes recently played songs (useful for testing)|
| `--clear-history` | off | Resets last played for all songs in the library (useful for testing or starting fresh)|


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

## Controls

```
SPACE    pause / resume
→        skip to next track
←        rewind / previous track
↑ / ↓    volume up / down
Q        quit
```

## Energy profiles

```
Steady    Consistent BPM and energy throughout
Build     Starts calm, ramps up to a high-energy finish
Pyramid   Builds to a peak at the halfway point then winds down
```

## Supported audio formats

`.mp3`, `.flac`, `.wav`, `.m4a`, `.ogg`, `.aiff`

## Personalisation

Edit `config/user_profile.json` to set your stride length (affects BPM calculation):

```json
{
  "stride_length_m": 2.2,
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
├── playback/        # Audio playback engine and input handler
├── results/         # Generated playlists (git-ignored)
├── songs/           # Your music folder (git-ignored)
├── tests/           # pytest test suite
└── main.py          # CLI entry point
```

## Running the tests

```bash
python -m pytest tests/ -v
```

## Project status

| Phase | Status | Description |
|---|---|---|
| 1 | ✅ Complete | CLI playlist generator |
| 2 | ✅ Complete | In-app playback, energy profiles, live controls |
| 3 | 🔲 Planned | Time stretching and section selection |
| 4 | 🔲 Planned | Voiceover cues and interval training |
| 5 | 🔲 Planned | Flask API |
| 6 | 🔲 Planned | Strava integration |
| 7 | 🔲 Planned | Live heart rate adaptive BPM |
| 8 | 🔲 Planned | Mobile app |