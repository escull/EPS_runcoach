from pathlib import Path

from eps_runcoach.core.fit_import import read_fit_session

SAMPLE_DIR = Path(__file__).parent.parent / "sample_data"


def test_read_fit_session_extracts_summary():
    fit_file = SAMPLE_DIR / "Treadmill_2026-09-08T18_29_35.fit"
    summary = read_fit_session(fit_file)

    assert summary.sport == "running"
    assert summary.sub_sport == "treadmill"
    assert summary.total_distance_km == 5.01
    assert summary.avg_heart_rate == 144
    assert summary.max_heart_rate == 161
    assert summary.total_duration_s == 1674.501


def test_read_fit_session_never_reads_gps_fields():
    fit_file = SAMPLE_DIR / "Treadmill_2026-09-08T18_29_35.fit"
    summary = read_fit_session(fit_file)

    field_names = vars(summary).keys()
    assert not any("lat" in name or "long" in name for name in field_names)
