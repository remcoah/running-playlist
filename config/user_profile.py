from __future__ import annotations

import json
import logging

from config.settings import USER_PROFILE_PATH

logger = logging.getLogger("running_playlist")

_DEFAULTS: dict = {
    "name": "",
    "stride_length_m": 2.2,
    "voiceover_enabled": True,
}


def load_profile() -> dict:
    """Read user_profile.json and return its contents, falling back to defaults on any error."""
    try:
        with open(USER_PROFILE_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("user_profile.json not found at %s — using defaults", USER_PROFILE_PATH)
    except json.JSONDecodeError as exc:
        logger.warning("user_profile.json is malformed (%s) — using defaults", exc)
    return dict(_DEFAULTS)
