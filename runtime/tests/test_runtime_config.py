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


def test_runtime_config_reads_repository_registry_from_yaml(monkeypatch, tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
repositories:
  - key: app
    name: app-service
    url: https://example.com/app.git
    default_branch: main
    enabled: true
  - key: disabled
    name: disabled-service
    url: https://example.com/disabled.git
    default_branch: develop
    enabled: false
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(config, "_runtime_config_path", lambda: config_path)
    config._load_runtime_config.cache_clear()

    assert [repo["key"] for repo in settings.registered_repositories] == [
        "app",
        "disabled",
    ]
    assert settings.enabled_repositories == [
        {
            "key": "app",
            "name": "app-service",
            "url": "https://example.com/app.git",
            "default_branch": "main",
            "enabled": True,
        }
    ]
    assert settings.get_repository("app")["name"] == "app-service"

    config._load_runtime_config.cache_clear()


def test_runtime_config_rejects_duplicate_repository_keys(monkeypatch, tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
repositories:
  - key: app
    name: app-service
    url: https://example.com/app.git
  - key: app
    name: app-copy
    url: https://example.com/app-copy.git
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(config, "_runtime_config_path", lambda: config_path)
    config._load_runtime_config.cache_clear()

    try:
        try:
            _ = settings.registered_repositories
        except ValueError as exc:
            assert "Duplicate repository key" in str(exc)
        else:
            raise AssertionError("expected duplicate repository key to fail")
    finally:
        config._load_runtime_config.cache_clear()
