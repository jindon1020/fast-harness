"""
Workspace isolation: each session gets a dedicated working directory.
"""

import shutil
from pathlib import Path

from src.config import settings


def get_session_workspace(session_id: str) -> Path:
    """Return the isolated workspace path for a session."""
    ws = Path(settings.workspace_root) / session_id
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def destroy_workspace(session_id: str) -> None:
    """Remove a session's workspace directory."""
    ws = Path(settings.workspace_root) / session_id
    if ws.exists():
        shutil.rmtree(ws)


def list_workspaces() -> list[str]:
    """List active session workspace IDs."""
    root = Path(settings.workspace_root)
    if not root.exists():
        return []
    return [d.name for d in root.iterdir() if d.is_dir()]
