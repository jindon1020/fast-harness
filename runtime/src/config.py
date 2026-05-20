from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    anthropic_api_key: str = ""
    anthropic_auth_token: str = ""
    anthropic_base_url: str = ""

    # Workspace isolation — each session gets <workspace_root>/<session_id>/
    workspace_root: str = "/workspaces"

    # Path to fast-harness plugin directory (relative to runtime/ or absolute)
    harness_plugin_path: str = "../plugin"

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


settings = Settings()
