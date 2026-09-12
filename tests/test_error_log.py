from eps_runcoach.core import error_log


def test_log_exception_writes_traceback(tmp_path, monkeypatch):
    log_path = tmp_path / "error.log"
    monkeypatch.setattr(error_log, "LOG_PATH", log_path)

    try:
        raise ValueError("something broke")
    except ValueError:
        returned_path = error_log.log_exception("Test context")

    assert returned_path == log_path
    content = log_path.read_text(encoding="utf-8")
    assert "Test context" in content
    assert "ValueError: something broke" in content


def test_log_exception_appends_rather_than_overwrites(tmp_path, monkeypatch):
    log_path = tmp_path / "error.log"
    monkeypatch.setattr(error_log, "LOG_PATH", log_path)

    for i in range(2):
        try:
            raise RuntimeError(f"failure {i}")
        except RuntimeError:
            error_log.log_exception(f"context {i}")

    content = log_path.read_text(encoding="utf-8")
    assert "failure 0" in content
    assert "failure 1" in content
