from pathlib import Path

# Project root — two levels up from this file (config/settings.py → config/ → project root)
BASE_DIR = Path(__file__).resolve().parent.parent

# BPM
DEFAULT_BPM_TOLERANCE: int = 10
BPM_MIN: int = 100   # lower bound for any realistic running cadence
BPM_MAX: int = 240   # upper bound for any realistic running cadence

# Warmup / cooldown phases (minutes)
WARMUP_MINS: int = 5
COOLDOWN_MINS: int = 5

# Energy thresholds used during warmup/cooldown filtering
WARMUP_MAX_ENERGY: float = 0.6
COOLDOWN_MAX_ENERGY: float = 0.5

# Recency filter — songs played within this window are excluded by default
RECENTLY_PLAYED_WINDOW_MINS: int = 10_080  # 7 days

# File paths — absolute, anchored to project root
SONG_LIBRARY_PATH = BASE_DIR / "music" / "song_library.json"
USER_PROFILE_PATH = BASE_DIR / "config" / "user_profile.json"
DEFAULT_MUSIC_FOLDER = BASE_DIR / "songs"

# Pace / distance assumptions
# Average distance covered per full gait cycle (left + right step) in metres
DEFAULT_STRIDE_LENGTH_M: float = 2.2
# One stride = 2 steps, so stride_rate * 2 gives steps/min which equals target BPM
AVERAGE_STEP_FREQUENCY_FACTOR: float = 2.0

# Output — generated artefacts go to results/, source modules stay in output/
OUTPUT_DIR = BASE_DIR / "results"
DEFAULT_OUTPUT_FORMAT: str = "m3u"
DEFAULT_OUTPUT_PATH = OUTPUT_DIR / "playlist"

# Logging
LOG_PATH = BASE_DIR / "logs" / "app.log"
LOG_LEVEL: str = "DEBUG"

# Playback
SLOT_DURATION_MINS: int = 4
CROSSFADE_DURATION_SECS: int = 8
DEFAULT_TRANSITION: str = "crossfade"
DEFAULT_ENERGY_PROFILE: str = "steady"
VOLUME_STEP: float = 0.05
INITIAL_VOLUME: float = 0.8
REPEAT_ALLOWED_AFTER: int = 5   # minimum slots between repeat plays of the same track
