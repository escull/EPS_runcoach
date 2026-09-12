from pathlib import Path

from eps_runcoach.core.fit_import import read_fit_session


def main() -> None:
    sample_dir = Path(__file__).parent.parent / "sample_data"
    fit_files = sorted(sample_dir.glob("*.fit"))

    if not fit_files:
        print(f"No .fit files found in {sample_dir}")
        return

    for fit_file in fit_files:
        summary = read_fit_session(fit_file)
        print(f"{summary.source_file}")
        print(f"  Sport:     {summary.sport} ({summary.sub_sport})")
        print(f"  Start:     {summary.start_time}")
        print(f"  Distance:  {summary.total_distance_km:.2f} km")
        print(f"  Duration:  {summary.total_duration_s / 60:.1f} min")
        print(f"  Avg pace:  {summary.avg_pace_min_per_km:.2f} min/km")
        print(f"  Avg HR:    {summary.avg_heart_rate} bpm (max {summary.max_heart_rate})")
        print()


if __name__ == "__main__":
    main()

