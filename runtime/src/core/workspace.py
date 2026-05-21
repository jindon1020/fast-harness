"""
Workspace manager — manages named workspaces containing one or more git repos.
Each workspace is a directory under <workspace_root>/<workspace_id>/.
"""

import json
import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.config import settings
from src.core.git import (
    create_worktree,
    pull,
    status as git_status,
    RepoInfo,
    branches as git_branches,
    checkout as git_checkout,
)

logger = logging.getLogger(__name__)


class WorkspaceStore:
    """File-based registry of workspaces and their repo configurations."""

    def __init__(self) -> None:
        self._dir = Path(settings.workspace_root) / ".workspaces"
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, ws_id: str) -> Path:
        return self._dir / f"{ws_id}.json"

    def _sanitize(self, name: str) -> str:
        """Convert workspace name to a safe directory name."""
        return name.lower().replace(" ", "-").replace("/", "-")

    def create(
        self,
        name: str,
        repo_url: Optional[str] = None,
        repo_name: Optional[str] = None,
        branch: Optional[str] = None,
    ) -> dict:
        ws_id = f"ws-{uuid.uuid4().hex[:10]}"
        ws_dir = Path(settings.workspace_root) / ws_id
        ws_dir.mkdir(parents=True, exist_ok=True)

        record = {
            "workspace_id": ws_id,
            "name": name,
            "cwd": str(ws_dir),
            "repos": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        self._path(ws_id).write_text(json.dumps(record, indent=2))

        try:
            self.add_repo(
                ws_id,
                repo_url or settings.default_project_git_url,
                repo_name or settings.default_project_repo_name,
                branch,
            )
        except Exception:
            self.delete(ws_id)
            raise

        result = self.get(ws_id)
        assert result is not None
        return result

    def get(self, ws_id: str) -> Optional[dict]:
        p = self._path(ws_id)
        if not p.exists():
            return None
        return json.loads(p.read_text())

    def list_all(self) -> list[dict]:
        if not self._dir.exists():
            return []
        records = []
        for f in sorted(self._dir.glob("*.json")):
            records.append(json.loads(f.read_text()))
        return records

    def delete(self, ws_id: str) -> None:
        record = self.get(ws_id)
        if record:
            for repo in record.get("repos", []):
                repo_path = repo.get("local_path")
                if repo_path:
                    self._remove_worktree(Path(repo_path))
        p = self._path(ws_id)
        if p.exists():
            p.unlink()
        ws_dir = Path(settings.workspace_root) / ws_id
        if ws_dir.exists():
            shutil.rmtree(ws_dir, ignore_errors=True)

    def _remove_worktree(self, repo_path: Path) -> None:
        if not repo_path.exists():
            return
        import subprocess

        subprocess.run(
            ["git", "worktree", "remove", "--force", str(repo_path)],
            cwd=str(repo_path.parent),
            capture_output=True,
            text=True,
            timeout=60,
        )

    def add_repo(self, ws_id: str, url: str, name: Optional[str] = None, branch: Optional[str] = None) -> RepoInfo:
        record = self.get(ws_id)
        if not record:
            raise ValueError(f"Workspace not found: {ws_id}")
        ws_dir = Path(record["cwd"])

        repo = create_worktree(
            url=url,
            source_dir=Path(settings.workspace_root) / ".sources",
            worktree_path=ws_dir / (name or settings.default_project_repo_name),
            branch=branch,
        )

        # Persist to workspace record
        record["repos"].append(repo.to_dict())
        record["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._path(ws_id).write_text(json.dumps(record, indent=2))

        return repo

    def pull_all(self, ws_id: str) -> list[dict]:
        record = self.get(ws_id)
        if not record:
            raise ValueError(f"Workspace not found: {ws_id}")
        results = []
        for r in record["repos"]:
            repo_path = Path(record["cwd"]) / r["name"]
            try:
                pull(repo_path)
                r["status"] = "ok"
            except Exception as exc:
                r["status"] = f"error: {exc}"
            results.append(r)
        record["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._path(ws_id).write_text(json.dumps(record, indent=2))
        return results

    def repo_status(self, ws_id: str, repo_name: str) -> dict:
        record = self.get(ws_id)
        if not record:
            raise ValueError(f"Workspace not found: {ws_id}")
        repo_path = Path(record["cwd"]) / repo_name
        s = git_status(repo_path)
        return {
            "repo": repo_name,
            "branch": s.branch,
            "ahead": s.ahead,
            "behind": s.behind,
            "modified": s.modified,
            "untracked": s.untracked,
            "clean": s.clean,
        }

    def list_branches(self, ws_id: str, repo_name: str) -> list[str]:
        record = self.get(ws_id)
        if not record:
            raise ValueError(f"Workspace not found: {ws_id}")
        repo_path = Path(record["cwd"]) / repo_name
        return git_branches(repo_path)

    def checkout_branch(self, ws_id: str, repo_name: str, branch: str) -> dict:
        record = self.get(ws_id)
        if not record:
            raise ValueError(f"Workspace not found: {ws_id}")
        repo_path = Path(record["cwd"]) / repo_name
        git_checkout(repo_path, branch)
        # Update branch in repo record
        for r in record["repos"]:
            if r["name"] == repo_name:
                r["branch"] = branch
        record["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._path(ws_id).write_text(json.dumps(record, indent=2))
        return {"repo": repo_name, "branch": branch, "status": "ok"}

workspace_store = WorkspaceStore()
