import shutil
from pathlib import Path

from eps_runcoach.core import db
from eps_runcoach.core.importer import import_files, import_folder

SAMPLE_DIR = Path(__file__).parent.parent / "sample_data"
TREADMILL_FIT = SAMPLE_DIR / "Treadmill_2026-09-08T18_29_35.fit"
OUTDOOR_RUN_FIT = SAMPLE_DIR / "Running_2026-08-19T18_21_10.fit"


def test_import_files_imports_new_sessions(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")

    summary = import_files([TREADMILL_FIT, OUTDOOR_RUN_FIT], conn)

    assert [name for name, _ in summary.imported] == [TREADMILL_FIT.name, OUTDOOR_RUN_FIT.name]
    assert all(isinstance(session_id, int) for _, session_id in summary.imported)
    assert summary.skipped == []
    assert summary.failed == []
    assert len(db.get_all_sessions(conn)) == 2


def test_importing_the_same_files_twice_skips_duplicates(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")

    import_files([TREADMILL_FIT], conn)
    summary = import_files([TREADMILL_FIT], conn)

    assert summary.imported == []
    assert summary.skipped == [(TREADMILL_FIT.name, "duplicate (already imported)")]
    assert len(db.get_all_sessions(conn)) == 1


def test_import_folder_imports_every_fit_file(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    shutil.copy(TREADMILL_FIT, inbox / TREADMILL_FIT.name)
    shutil.copy(OUTDOOR_RUN_FIT, inbox / OUTDOOR_RUN_FIT.name)
    (inbox / "not_a_fit_file.txt").write_text("ignore me")

    conn = db.get_connection(tmp_path / "test.db")
    summary = import_folder(inbox, conn)

    assert len(summary.imported) == 2
    assert len(db.get_all_sessions(conn)) == 2


def test_import_files_records_unparseable_file_as_failed_not_a_crash(tmp_path):
    bad_file = tmp_path / "corrupt.fit"
    bad_file.write_bytes(b"this is not a real FIT file")

    conn = db.get_connection(tmp_path / "test.db")
    summary = import_files([TREADMILL_FIT, bad_file], conn)

    assert [name for name, _ in summary.imported] == [TREADMILL_FIT.name]
    assert len(summary.failed) == 1
    assert summary.failed[0][0] == "corrupt.fit"
    assert len(db.get_all_sessions(conn)) == 1


def test_import_files_backs_up_database_before_each_batch(tmp_path):
    db_path = tmp_path / "test.db"
    conn = db.get_connection(db_path)

    import_files([TREADMILL_FIT], conn)
    import_files([OUTDOOR_RUN_FIT], conn)

    # every import batch backs up first, so two batches make two backups
    backups = list((tmp_path / "backups").glob("test_*.db"))
    assert len(backups) == 2


def test_classified_session_type_is_stored(tmp_path):
    conn = db.get_connection(tmp_path / "test.db")
    import_files([TREADMILL_FIT], conn)

    row = db.get_all_sessions(conn)[0]
    assert row["session_type"] == "run"
