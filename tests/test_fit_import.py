from pathlib import Path

from eps_runcoach.core.fit_import import parse_fit_file

SAMPLE_DIR = Path(__file__).parent.parent / "sample_data"
TREADMILL_FIT = SAMPLE_DIR / "Treadmill_2026-09-08T18_29_35.fit"


def test_parse_fit_file_extracts_summary():
    parsed = parse_fit_file(TREADMILL_FIT)
    summary = parsed.summary

    assert summary.sport == "running"
    assert summary.sub_sport == "treadmill"
    assert summary.total_distance_km == 5.01
    assert summary.avg_heart_rate == 144
    assert summary.max_heart_rate == 161
    assert summary.total_duration_s == 1674.501


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
