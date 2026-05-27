from __future__ import annotations
from dataclasses import dataclass


@dataclass
class RunContext:
    duration_mins: float
    target_bpm: int
    bpm_tolerance: int
    source: str           # "manual" in Phase 1
    live_hr: int | None   # always None in Phase 1
