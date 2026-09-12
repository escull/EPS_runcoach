from datetime import date

import numpy as np
import pytest

from eps_runcoach.core import metrics


def test_hrr_fraction_basic():
    # resting 60, max 190: HR 125 is exactly 50% HRR
    assert metrics.hrr_fraction(125, resting_hr=60, max_hr=190) == pytest.approx(0.5)


def test_hrr_fraction_clamped_to_zero_when_below_resting():
    assert metrics.hrr_fraction(40, resting_hr=60, max_hr=190) == 0.0


def test_hrr_fraction_none_when_max_not_above_resting():
    assert metrics.hrr_fraction(150, resting_hr=190, max_hr=190) is None


def test_trimp_increases_with_intensity():
    low = metrics.trimp(avg_hr=120, duration_s=1800, resting_hr=60, max_hr=190)
    high = metrics.trimp(avg_hr=170, duration_s=1800, resting_hr=60, max_hr=190)
    assert low > 0
    assert high > low


def test_trimp_none_without_avg_hr_or_duration():
    assert metrics.trimp(None, 1800, 60, 190) is None
    assert metrics.trimp(140, None, 60, 190) is None


def test_srpe_load():
    assert metrics.srpe_load(rpe=7, duration_s=3600) == pytest.approx(7 * 60)


def test_srpe_load_none_without_rpe():
    assert metrics.srpe_load(None, 3600) is None


def test_combined_session_load_takes_the_larger_value():
    assert metrics.combined_session_load(trimp_value=50, srpe_value=80) == 80
    assert metrics.combined_session_load(trimp_value=90, srpe_value=30) == 90


def test_combined_session_load_falls_back_to_whichever_exists():
    assert metrics.combined_session_load(None, 40) == 40
    assert metrics.combined_session_load(60, None) == 60
    assert metrics.combined_session_load(None, None) is None


def test_time_in_zones_buckets_correctly():
    # resting 60, max 190 (range 130): zone boundaries in bpm are
    # 60,138,151,164,177,255 approx for fractions 0,.6,.7,.8,.9,1.5
    heart_rates = [100, 145, 160, 175, 185, None]  # last one unclassifiable
    zones = metrics.time_in_zones(heart_rates, sample_interval_s=5.0, resting_hr=60, max_hr=190)

    assert len(zones) == 5
    assert sum(zones) == 5.0 * 5  # 5 classifiable samples x 5s each
    assert zones[0] == 5.0  # HR 100 -> ~30% HRR -> zone 1


def test_ewma_matches_manual_recursion():
    values = np.array([10.0, 0.0, 0.0, 20.0])
    result = metrics.ewma(values, span=6)

    alpha = 2 / 7
    expected = [10.0]
    for v in values[1:]:
        expected.append(alpha * v + (1 - alpha) * expected[-1])

    assert result == pytest.approx(expected)


def test_daily_load_series_fills_gaps_with_zero():
    loads = [(date(2026, 1, 1), 50.0), (date(2026, 1, 3), 30.0)]
    dates, daily = metrics.daily_load_series(loads)

    assert dates == [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]
    assert list(daily) == [50.0, 0.0, 30.0]


def test_daily_load_series_sums_same_day_sessions():
    loads = [(date(2026, 1, 1), 20.0), (date(2026, 1, 1), 15.0)]
    dates, daily = metrics.daily_load_series(loads)

    assert dates == [date(2026, 1, 1)]
    assert list(daily) == [35.0]


def test_fitness_fatigue_form_shapes_and_form_equals_difference():
    loads = [(date(2026, 1, 1), 50.0), (date(2026, 1, 2), 0.0), (date(2026, 1, 3), 80.0)]
    dates, fitness, fatigue, form = metrics.fitness_fatigue_form(loads)

    assert len(dates) == len(fitness) == len(fatigue) == len(form) == 3
    assert form == pytest.approx(fitness - fatigue)


def test_aerobic_efficiency_pace_averages_matching_samples():
    # easy HR at 65% HRR with resting 60, max 190 = 60 + 0.65*130 = 144.5
    heart_rates = [144, 145, 170]
    speeds = [3.0, 3.2, 5.0]  # third sample well outside HR tolerance
    pace = metrics.aerobic_efficiency_pace(heart_rates, speeds, resting_hr=60, max_hr=190)

    expected_avg_speed = (3.0 + 3.2) / 2
    expected_pace = (1000 / expected_avg_speed) / 60
    assert pace == pytest.approx(expected_pace)


def test_aerobic_efficiency_pace_none_when_no_samples_qualify():
    pace = metrics.aerobic_efficiency_pace([100, 110], [3.0, 3.1], resting_hr=60, max_hr=190)
    assert pace is None


def test_estimate_5k_seconds_uses_best_recent_run():
    today = date(2026, 9, 1)
    runs = [
        (date(2026, 8, 20), 5.0, 1500.0),  # exactly 25:00 for 5k
        (date(2026, 8, 25), 10.0, 2700.0),  # 45:00 for 10k -> scales faster
        (date(2026, 6, 1), 5.0, 1200.0),  # fast but too old (outside lookback)
    ]
    estimate = metrics.estimate_5k_seconds(runs, as_of=today)

    scaled_10k = 2700.0 * (5.0 / 10.0) ** 1.06
    assert estimate == pytest.approx(min(1500.0, scaled_10k))


def test_estimate_5k_seconds_ignores_short_runs_and_returns_none_if_no_candidates():
    today = date(2026, 9, 1)
    runs = [(date(2026, 8, 30), 1.0, 300.0)]  # below min_distance_km
    assert metrics.estimate_5k_seconds(runs, as_of=today) is None
    assert metrics.estimate_5k_seconds([], as_of=today) is None
