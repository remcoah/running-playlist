from config.settings import (
    AVERAGE_STEP_FREQUENCY_FACTOR,
    BPM_MAX,
    BPM_MIN,
    DEFAULT_BPM_TOLERANCE,
    DEFAULT_STRIDE_LENGTH_M,
)
from core.run_context import RunContext


def build_run_context(
    distance_km: float,
    pace_min_per_km: float,
    tolerance: int = DEFAULT_BPM_TOLERANCE,
    stride_length_m: float = DEFAULT_STRIDE_LENGTH_M,
) -> RunContext:
    """Calculate run duration and target BPM from distance and pace, and return a RunContext."""
    if distance_km <= 0:
        raise ValueError(f"distance_km must be positive, got {distance_km}")
    if pace_min_per_km <= 0:
        raise ValueError(f"pace_min_per_km must be positive, got {pace_min_per_km}")

    # Total run time in minutes
    duration_mins = distance_km * pace_min_per_km

    # Convert pace to BPM via cadence:
    #   speed (m/min) = 1000 / pace
    #   stride_rate (strides/min) = speed / stride_length
    #   target_bpm (steps/min) = stride_rate * 2  (one stride = two steps)
    speed_m_per_min = 1000.0 / pace_min_per_km
    stride_rate = speed_m_per_min / stride_length_m
    target_bpm = int(round(stride_rate * AVERAGE_STEP_FREQUENCY_FACTOR))
    if not (BPM_MIN <= target_bpm <= BPM_MAX):
        raise ValueError(
            f"Calculated BPM {target_bpm} is outside the valid range "
            f"[{BPM_MIN}, {BPM_MAX}]. Check --distance and --pace."
        )

    return RunContext(
        duration_mins=duration_mins,
        target_bpm=target_bpm,
        bpm_tolerance=tolerance,
        source="manual",
        live_hr=None,
    )
