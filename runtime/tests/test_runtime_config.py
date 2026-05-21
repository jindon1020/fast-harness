from pathlib import Path

from src import config
from src.config import settings


def test_runtime_config_reads_stream_options_from_yaml(monkeypatch, tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
stream:
  visible_tools:
    - Bash
    - Grep
  show_thinking: false
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(config, "_runtime_config_path", lambda: config_path)
    config._load_runtime_config.cache_clear()

    assert settings.runtime_config_path == config_path
    assert settings.stream_visible_tools == ["Bash", "Grep"]
    assert settings.stream_show_thinking is False

    config._load_runtime_config.cache_clear()


def test_runtime_config_defaults_when_yaml_is_missing(monkeypatch, tmp_path):
    missing_path = tmp_path / "missing.yaml"

    monkeypatch.setattr(config, "_runtime_config_path", lambda: missing_path)
    config._load_runtime_config.cache_clear()

    assert settings.stream_visible_tools == []
    assert settings.stream_show_thinking is True

    config._load_runtime_config.cache_clear()
