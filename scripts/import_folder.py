"""Command-line FIT file importer.

Usage:
    uv run python scripts/import_folder.py <folder> [--db PATH]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from eps_runcoach.core import db
from eps_runcoach.core.importer import import_folder


def main() -> None:
    parser = argparse.ArgumentParser(description="Import FIT files from a folder into the database.")
    parser.add_argument("folder", type=Path, help="Folder containing .fit files")
    parser.add_argument("--db", type=Path, default=db.DEFAULT_DB_PATH, help="Path to the database file")
    args = parser.parse_args()

    conn = db.get_connection(args.db)
    try:
        summary = import_folder(args.folder, conn)
    finally:
        conn.close()

    print(f"Imported ({len(summary.imported)}):")
    for name, _session_id in summary.imported:
        print(f"  + {name}")

    print(f"Skipped ({len(summary.skipped)}):")
    for name, reason in summary.skipped:
        print(f"  - {name}: {reason}")

    print(f"Failed ({len(summary.failed)}):")
    for name, reason in summary.failed:
        print(f"  ! {name}: {reason}")


if __name__ == "__main__":
    main()
