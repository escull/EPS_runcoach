from eps_runcoach.core.formatting import (
    format_date,
    format_distance,
    format_duration,
    format_hr,
    format_pace,
    parse_mmss_to_seconds,
)


def test_format_date_from_iso_string():
    assert format_date("2026-08-19T17:21:10+00:00") == "19/08/2026"


def test_format_date_handles_none():
    assert format_date(None) == "-"


def test_format_duration_under_an_hour():
    assert format_duration(125) == "2:05"


def test_format_duration_over_an_hour():
    assert format_duration(3725) == "1:02:05"


def test_format_duration_handles_none():
    assert format_duration(None) == "-"


def test_format_distance():
    assert format_distance(5.008) == "5.01 km"


def test_format_pace_rounds_seconds():
    assert format_pace(5.0) == "5:00 /km"
    assert format_pace(4.999) == "5:00 /km"


def test_format_pace_handles_none_or_zero():
    assert format_pace(None) == "-"
    assert format_pace(0) == "-"


def test_format_hr():
    assert format_hr(153) == "153 bpm"
    assert format_hr(None) == "-"


def test_parse_mmss_to_seconds():
    assert parse_mmss_to_seconds("25:00") == 1500.0
    assert parse_mmss_to_seconds("1:02:05") == 3725.0


def test_parse_mmss_to_seconds_rejects_invalid_input():
    assert parse_mmss_to_seconds("not a time") is None
    assert parse_mmss_to_seconds("25:99") is None
    assert parse_mmss_to_seconds("25") is None
    assert parse_mmss_to_seconds("") is None
