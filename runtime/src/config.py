from pathlib import Path
from functools import lru_cache
from typing import Any

from pydantic_settings import BaseSettings
import yaml


def _runtime_config_path() -> Path:
    return Path(__file__).resolve().parent.parent / "config.yaml"


@lru_cache(maxsize=1)
def _load_runtime_config() -> dict[str, Any]:
    path = _runtime_config_path()
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Runtime config must be a YAML mapping: {path}")
    return data


def _stream_config() -> dict[str, Any]:
    stream = _load_runtime_config().get("stream", {})
    if stream is None:
        return {}
    if not isinstance(stream, dict):
        raise ValueError("runtime config key 'stream' must be a YAML mapping")
    return stream


def _repository_configs() -> list[dict[str, Any]]:
    repositories = _load_runtime_config().get("repositories", [])
    if repositories is None:
        return []
    if not isinstance(repositories, list):
        raise ValueError("runtime config key 'repositories' must be a YAML list")

    seen_keys: set[str] = set()
    seen_names: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for raw_repo in repositories:
        if not isinstance(raw_repo, dict):
            raise ValueError("each repository config must be a YAML mapping")
        key = str(raw_repo.get("key", "")).strip()
        name = str(raw_repo.get("name", key)).strip()
        url = str(raw_repo.get("url", "")).strip()
        if not key:
            raise ValueError("repository config is missing required key 'key'")
        if not name:
            raise ValueError(f"repository {key!r} is missing required key 'name'")
        if not url:
            raise ValueError(f"repository {key!r} is missing required key 'url'")
        if key in seen_keys:
            raise ValueError(f"Duplicate repository key: {key}")
        if name in seen_names:
            raise ValueError(f"Duplicate repository name: {name}")
        seen_keys.add(key)
        seen_names.add(name)
        normalized.append(
            {
                "key": key,
                "name": name,
                "url": url,
                "default_branch": str(raw_repo.get("default_branch", "main")).strip() or "main",
                "enabled": bool(raw_repo.get("enabled", True)),
            }
        )
    return normalized


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    anthropic_api_key: str = ""
    anthropic_auth_token: str = ""
    anthropic_base_url: str = ""

    # Workspace isolation — each session gets <workspace_root>/<session_id>/
    workspace_root: str = "/workspaces"

    # Path to fast-harness plugin directory (relative to runtime/ or absolute)
    harness_plugin_path: str = "../plugin"

    # Default project repo used when creating user workspaces.
    default_project_git_url: str = "https://codeup.aliyun.com/64802395702c0cacad997dc6/backend/video-creation-tool/creation-tool.git"
    default_project_repo_name: str = "creation-tool"

    # Git credentials
    git_github_token: str = ""
    git_codeup_user: str = ""
    git_codeup_token: str = ""
    git_ssh_key_path: str = ""
    git_default_branch: str = "main"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Default agent limits
    default_max_turns: int = 30
    default_max_budget_usd: float = 10.0
    session_cleanup_days: int = 7

    log_level: str = "INFO"

    @property
    def resolved_harness_path(self) -> Path:
        p = Path(self.harness_plugin_path)
        if not p.is_absolute():
            p = Path(__file__).resolve().parent.parent / p
        return p.resolve()

    @property
    def runtime_config_path(self) -> Path:
        return _runtime_config_path()

    @property
    def stream_visible_tools(self) -> list[str]:
        visible_tools = _stream_config().get("visible_tools", [])
        if visible_tools is None:
            return []
        if isinstance(visible_tools, str):
            return [
                name.strip()
                for name in visible_tools.split(",")
                if name.strip()
            ]
        if isinstance(visible_tools, list):
            return [
                str(name).strip()
                for name in visible_tools
                if str(name).strip()
            ]
        raise ValueError("runtime config key 'stream.visible_tools' must be a list")

    @property
    def stream_show_thinking(self) -> bool:
        value = _stream_config().get("show_thinking", True)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @property
    def registered_repositories(self) -> list[dict[str, Any]]:
        return _repository_configs()

    @property
    def enabled_repositories(self) -> list[dict[str, Any]]:
        return [
            repo
            for repo in self.registered_repositories
            if repo.get("enabled", True)
        ]

    def get_repository(self, key: str) -> dict[str, Any]:
        for repo in self.enabled_repositories:
            if repo["key"] == key:
                return repo
        raise ValueError(f"Repository not found or disabled: {key}")


settings = Settings()
