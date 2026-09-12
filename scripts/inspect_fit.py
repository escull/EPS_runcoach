"""Print a summary of every .fit file in a folder (sample_data/ by default).

Usage:
    uv run python scripts/inspect_fit.py [folder]
"""

from __future__ import annotations

import sys
from pathlib import Path

from eps_runcoach.core.fit_import import parse_fit_file


def main() -> None:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "sample_data"
    fit_files = sorted(folder.glob("*.fit"))

    if not fit_files:
        print(f"No .fit files found in {folder}")
        return

    for fit_file in fit_files:
        parsed = parse_fit_file(fit_file)
        summary = parsed.summary
        print(f"{summary.source_file}")
        print(f"  Sport:     {summary.sport} ({summary.sub_sport})")
        print(f"  Start:     {summary.start_time}")
        print(f"  Distance:  {summary.total_distance_km:.2f} km")
        print(f"  Duration:  {summary.total_duration_s / 60:.1f} min")
        print(f"  Avg pace:  {summary.avg_pace_min_per_km:.2f} min/km")
        print(f"  Avg HR:    {summary.avg_heart_rate} bpm (max {summary.max_heart_rate})")
        print(f"  Splits:    {len(parsed.splits)}")
        print(f"  Samples:   {len(parsed.samples)} (every 5s)")
        print()


if __name__ == "__main__":
    main()
