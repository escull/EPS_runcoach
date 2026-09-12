from pathlib import Path

from eps_runcoach.core import app_paths


def test_not_frozen_in_normal_test_run():
    assert app_paths.is_frozen() is False


def test_get_data_dir_is_relative_data_folder_when_not_frozen():
    assert app_paths.get_data_dir() == Path("data")


def test_get_env_path_is_project_root_dot_env_when_not_frozen():
    env_path = app_paths.get_env_path()
    assert env_path.name == ".env"
    assert env_path.parent == Path(__file__).resolve().parent.parent


def test_get_data_dir_uses_appdata_when_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(app_paths.sys, "frozen", True, raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path))

    data_dir = app_paths.get_data_dir()

    assert data_dir == tmp_path / "EPS RunCoach"


def test_get_env_path_uses_data_dir_when_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(app_paths.sys, "frozen", True, raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path))

    env_path = app_paths.get_env_path()

    assert env_path == tmp_path / "EPS RunCoach" / ".env"
