import os

from eps_runcoach.core.coach.api_key import get_api_key, set_api_key


def test_get_api_key_returns_empty_when_file_missing(tmp_path):
    assert get_api_key(tmp_path / ".env") == ""


def test_set_then_get_api_key_round_trips(tmp_path):
    env_path = tmp_path / ".env"
    set_api_key("my-real-key-123", env_path)

    assert get_api_key(env_path) == "my-real-key-123"
    assert "my-real-key-123" in env_path.read_text()


def test_get_api_key_treats_placeholder_as_unset(tmp_path):
    env_path = tmp_path / ".env"
    set_api_key("paste-your-key-here", env_path)

    assert get_api_key(env_path) == ""


def test_set_api_key_updates_os_environ(tmp_path):
    original = os.environ.get("GEMINI_API_KEY")
    try:
        env_path = tmp_path / ".env"
        set_api_key("another-key-456", env_path)
        assert os.environ["GEMINI_API_KEY"] == "another-key-456"
    finally:
        if original is None:
            os.environ.pop("GEMINI_API_KEY", None)
        else:
            os.environ["GEMINI_API_KEY"] = original
