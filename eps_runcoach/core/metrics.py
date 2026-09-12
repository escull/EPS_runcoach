"""Training load metrics: HR zones, TRIMP, session-RPE load, fitness/
fatigue/form, aerobic efficiency, and a 5k time estimate.

These are estimates, not truths - heart rate tends to underestimate how
demanding strength work is, which is why session-RPE load matters
alongside TRIMP for gym sessions (see combined_session_load).
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np

# HR zones as fractions of heart-rate reserve (Karvonen method): [0-60%),
# [60-70%), [70-80%), [80-90%), [90%+). Chosen to line up with the HRR
# fraction TRIMP already uses, rather than a separate %HRmax convention.
ZONE_BOUNDARIES = (0.0, 0.60, 0.70, 0.80, 0.90, 1.5)
NUM_ZONES = len(ZONE_BOUNDARIES) - 1

# Banister TRIMP coefficients (the commonly-used single set, not gender-
# differentiated - this app has no gender setting).
TRIMP_COEFFICIENT = 0.64
TRIMP_EXPONENT_FACTOR = 1.92

FITNESS_SPAN_DAYS = 42
FATIGUE_SPAN_DAYS = 7

# "Fixed easy heart rate" for aerobic efficiency: mid-Zone-2, i.e. 65% HRR.
EASY_HRR_FRACTION = 0.65
EASY_HR_TOLERANCE_BPM = 3

RIEGEL_EXPONENT = 1.06
FIVE_K_KM = 5.0
RECENT_BEST_LOOKBACK_DAYS = 28
MIN_DISTANCE_FOR_ESTIMATE_KM = 2.0


def hrr_fraction(hr: float, resting_hr: float, max_hr: float) -> float | None:
    """Fraction of heart-rate reserve (Karvonen). None if max_hr <= resting_hr
    (misconfigured settings) rather than dividing by zero/negative.
    """
    if max_hr <= resting_hr:
        return None
    fraction = (hr - resting_hr) / (max_hr - resting_hr)
    return max(0.0, min(fraction, 1.5))


def trimp(avg_hr: float | None, duration_s: float | None, resting_hr: float, max_hr: float) -> float | None:
    """Banister TRIMP for one session, from its average heart rate."""
    if not avg_hr or not duration_s:
        return None
    fraction = hrr_fraction(avg_hr, resting_hr, max_hr)
    if fraction is None:
        return None
    duration_min = duration_s / 60
    return duration_min * fraction * TRIMP_COEFFICIENT * np.exp(TRIMP_EXPONENT_FACTOR * fraction)


def srpe_load(rpe: int | None, duration_s: float | None) -> float | None:
    """Session-RPE load: RPE x minutes. None if there's no logged RPE."""
    if not rpe or not duration_s:
        return None
    return rpe * (duration_s / 60)


def combined_session_load(trimp_value: float | None, srpe_value: float | None) -> float | None:
    """The larger of TRIMP and session-RPE load, since HR-based load tends
    to underestimate strength work. None only if neither is available.
    """
    values = [v for v in (trimp_value, srpe_value) if v is not None]
    return max(values) if values else None


def time_in_zones(heart_rates: list[float | None], sample_interval_s: float, resting_hr: float, max_hr: float) -> list[float]:
    """Seconds spent in each of the 5 HR zones across a sample stream.
    Samples with no heart rate reading are skipped (can't classify them).
    """
    seconds_per_zone = [0.0] * NUM_ZONES
    for hr in heart_rates:
        if hr is None:
            continue
        fraction = hrr_fraction(hr, resting_hr, max_hr)
        if fraction is None:
            continue
        for zone_index in range(NUM_ZONES):
            if ZONE_BOUNDARIES[zone_index] <= fraction < ZONE_BOUNDARIES[zone_index + 1]:
                seconds_per_zone[zone_index] += sample_interval_s
                break
    return seconds_per_zone


def ewma(values: np.ndarray, span: int) -> np.ndarray:
    """Exponentially weighted moving average, equivalent to pandas'
    ewm(span=span, adjust=False) - a plain numpy loop rather than adding
    pandas as a dependency for one calculation.
    """
    alpha = 2 / (span + 1)
    result = np.empty_like(values, dtype=float)
    if len(values) == 0:
        return result
    result[0] = values[0]
    for i in range(1, len(values)):
        result[i] = alpha * values[i] + (1 - alpha) * result[i - 1]
    return result


def daily_load_series(session_loads: list[tuple[date, float]]) -> tuple[list[date], np.ndarray]:
    """Build a continuous daily series from the earliest to the latest
    session date, summing same-day loads and filling gaps with 0 so the
    exponential averages decay properly across rest days.
    """
    if not session_loads:
        return [], np.array([])

    totals_by_day: dict[date, float] = {}
    for day, load in session_loads:
        totals_by_day[day] = totals_by_day.get(day, 0.0) + load

    start = min(totals_by_day)
    end = max(totals_by_day)
    num_days = (end - start).days + 1

    dates = [start + timedelta(days=i) for i in range(num_days)]
    loads = np.array([totals_by_day.get(d, 0.0) for d in dates])
    return dates, loads


def fitness_fatigue_form(session_loads: list[tuple[date, float]]) -> tuple[list[date], np.ndarray, np.ndarray, np.ndarray]:
    """Daily fitness (42-day EWMA), fatigue (7-day EWMA) and form
    (fitness - fatigue), from a list of (date, combined_session_load).
    """
    dates, daily_loads = daily_load_series(session_loads)
    fitness = ewma(daily_loads, FITNESS_SPAN_DAYS)
    fatigue = ewma(daily_loads, FATIGUE_SPAN_DAYS)
    form = fitness - fatigue
    return dates, fitness, fatigue, form


def aerobic_efficiency_pace(
    heart_rates: list[float | None],
    speeds_m_s: list[float | None],
    resting_hr: float,
    max_hr: float,
) -> float | None:
    """Average pace (min/km) across samples within EASY_HR_TOLERANCE_BPM of
    the fixed easy heart rate (65% HRR). None if no sample qualifies.
    """
    easy_hr = resting_hr + EASY_HRR_FRACTION * (max_hr - resting_hr)

    matching_speeds = [
        speed
        for hr, speed in zip(heart_rates, speeds_m_s)
        if hr is not None and speed and abs(hr - easy_hr) <= EASY_HR_TOLERANCE_BPM
    ]
    if not matching_speeds:
        return None

    avg_speed = sum(matching_speeds) / len(matching_speeds)
    return (1000 / avg_speed) / 60


def estimate_5k_seconds(
    runs: list[tuple[date, float, float]],
    as_of: date,
    lookback_days: int = RECENT_BEST_LOOKBACK_DAYS,
    min_distance_km: float = MIN_DISTANCE_FOR_ESTIMATE_KM,
) -> float | None:
    """Estimate current 5k time using Riegel's formula (T2 = T1 x (D2/D1)^1.06)
    applied to the best (fastest-scaling) recent run of at least
    min_distance_km, from the last lookback_days. None if no run qualifies.
    """
    cutoff = as_of - timedelta(days=lookback_days)
    candidates = [
        duration_s * (FIVE_K_KM / distance_km) ** RIEGEL_EXPONENT
        for session_date, distance_km, duration_s in runs
        if session_date >= cutoff and distance_km >= min_distance_km and duration_s
    ]
    return min(candidates) if candidates else None
