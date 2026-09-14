from pathlib import Path

import pytest

from eps_runcoach.core.fit_import import parse_fit_file

SAMPLE_DIR = Path(__file__).parent.parent / "sample_data"
TREADMILL_FIT = SAMPLE_DIR / "Treadmill_2026-09-08T18_29_35.fit"
TREADMILL_WITH_HRM_FIT = SAMPLE_DIR / "Treadmill_2026-09-14T18_16_37.fit"
CYCLING_FIT = SAMPLE_DIR / "Cycling_2026-08-16T13_11_22.fit"


def test_parse_fit_file_extracts_summary():
    parsed = parse_fit_file(TREADMILL_FIT)
    summary = parsed.summary

    assert summary.sport == "running"
    assert summary.sub_sport == "treadmill"
    assert summary.total_distance_km == 5.01
    assert summary.avg_heart_rate == 144
    assert summary.max_heart_rate == 161
    assert summary.total_duration_s == 1674.501


def test_pace_is_derived_from_distance_and_duration_not_avg_speed():
    # This file's avg_speed implies ~4350m over the recorded duration, but
    # total_distance is 5010m - a real example of a manually-corrected
    # treadmill distance where the watch's own speed stream wasn't updated
    # to match. Pace must follow the corrected distance, not avg_speed.
    parsed = parse_fit_file(TREADMILL_FIT)
    summary = parsed.summary

    expected_pace = (summary.total_duration_s / 60) / summary.total_distance_km
    assert summary.avg_pace_min_per_km == pytest.approx(expected_pace)
    assert summary.avg_pace_min_per_km == pytest.approx(5.5705, abs=1e-3)


def test_parse_fit_file_extracts_splits():
    parsed = parse_fit_file(TREADMILL_FIT)

    assert len(parsed.splits) == 5
    first_split = parsed.splits[0]
    assert first_split.split_index == 1
    assert first_split.distance_km == 1.0
    assert first_split.avg_heart_rate == 136


def test_parse_fit_file_extracts_downsampled_samples():
    parsed = parse_fit_file(TREADMILL_FIT)

    assert len(parsed.samples) > 0
    # ~1674s of recording at one row per 5s should be roughly 335 samples,
    # not the ~1669 raw per-second records in the file.
    assert len(parsed.samples) < 400

    elapsed_values = [s.elapsed_s for s in parsed.samples]
    assert elapsed_values == sorted(elapsed_values)
    assert all(s % 5 == 0 for s in elapsed_values)

    # every sample should have picked up a heart rate reading somewhere in
    # its 5-second bucket
    assert any(s.heart_rate is not None for s in parsed.samples)


def test_parse_fit_file_never_reads_gps_fields():
    parsed = parse_fit_file(TREADMILL_FIT)

    for obj in [parsed.summary, *parsed.splits, *parsed.samples]:
        field_names = vars(obj).keys()
        assert not any("lat" in name or "long" in name for name in field_names)


def test_parse_fit_file_extracts_recovery_and_training_effect_regardless_of_sport():
    # recovery_time and total_training_effect are computed by the watch from
    # heart rate alone, so they show up even on a non-running session.
    parsed = parse_fit_file(CYCLING_FIT)
    summary = parsed.summary

    assert summary.recovery_time_s == 6180
    assert summary.total_training_effect == pytest.approx(1.6)


def test_parse_fit_file_estimated_vo2_max_is_running_specific():
    # Suunto only estimates VO2 max for running activities - a cycling
    # session shouldn't claim a running fitness number it doesn't have.
    parsed = parse_fit_file(CYCLING_FIT)

    assert parsed.summary.estimated_vo2_max is None


def test_parse_fit_file_extracts_hrm_derived_fields_for_a_run():
    parsed = parse_fit_file(TREADMILL_WITH_HRM_FIT)
    summary = parsed.summary

    assert summary.estimated_vo2_max == pytest.approx(42.1, abs=0.1)
    assert summary.recovery_time_s == 28980
    assert summary.total_training_effect == pytest.approx(3.0)
