"""
Workspace manager — manages named workspaces containing one or more git repos.
Each workspace is a directory under <workspace_root>/<workspace_id>/.
"""

import json
import logging
import shutil
import subprocess
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
    remote_branches as git_remote_branches,
    checkout as git_checkout,
    normalize_branch_name,
)

logger = logging.getLogger(__name__)


class WorkspaceStore:
    """File-based registry of workspaces and their repo configurations."""

    def __init__(self) -> None:
        self._dir = Path(settings.workspace_root) / ".workspaces"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._backfill_legacy_users()

    def _path(self, ws_id: str) -> Path:
        return self._dir / f"{ws_id}.json"

    def _backfill_legacy_users(self) -> None:
        for path in self._dir.glob("*.json"):
            record = json.loads(path.read_text())
            if record.get("user_id"):
                continue
            record["user_id"] = settings.default_user_id
            record["updated_at"] = datetime.now(timezone.utc).isoformat()
            path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    def _sanitize(self, name: str) -> str:
        """Convert workspace name to a safe directory name."""
        return name.lower().replace(" ", "-").replace("/", "-")

    def create(
        self,
        name: str,
        repositories: Optional[list[dict]] = None,
        repo_url: Optional[str] = None,
        repo_name: Optional[str] = None,
        branch: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        ws_id = f"ws-{uuid.uuid4().hex[:10]}"
        ws_dir = Path(settings.workspace_root) / ws_id
        ws_dir.mkdir(parents=True, exist_ok=True)

        record = {
            "workspace_id": ws_id,
            "name": name,
            "cwd": str(ws_dir),
            "repos": [],
            "user_id": user_id or settings.default_user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        self._path(ws_id).write_text(json.dumps(record, indent=2))

        try:
            repo_specs = repositories
            if repo_specs is None and repo_url:
                repo_specs = [{
                    "url": repo_url,
                    "name": repo_name or settings.default_project_repo_name,
                    "branch": branch,
                }]
            if not repo_specs:
                raise ValueError("Workspace requires at least one git repository")

            for repo in repo_specs:
                self.add_repo(
                    ws_id,
                    repo["url"],
                    repo.get("name"),
                    repo.get("branch"),
                    user_id=record["user_id"],
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

    def rename(self, ws_id: str, name: str) -> dict:
        record = self.get(ws_id)
        if not record:
            raise ValueError(f"Workspace not found: {ws_id}")
        record["name"] = name.strip()
        record["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._path(ws_id).write_text(json.dumps(record, indent=2), encoding="utf-8")
        return record

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

        source_repo = Path(settings.workspace_root) / ".sources" / repo_path.name
        cwd = source_repo if source_repo.exists() else repo_path.parent
        result = subprocess.run(
            ["git", "worktree", "remove", "--force", str(repo_path)],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            logger.warning(
                "Failed to remove git worktree %s: %s",
                repo_path,
                result.stderr.strip() or result.stdout.strip() or "unknown error",
            )
            prune = subprocess.run(
                ["git", "worktree", "prune"],
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if prune.returncode != 0:
                logger.warning(
                    "Failed to prune git worktrees for %s: %s",
                    cwd,
                    prune.stderr.strip() or prune.stdout.strip() or "unknown error",
                )

    def add_repo(
        self,
        ws_id: str,
        url: str,
        name: Optional[str] = None,
        branch: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> RepoInfo:
        record = self.get(ws_id)
        if not record:
            raise ValueError(f"Workspace not found: {ws_id}")
        owner_id = user_id or record.get("user_id") or settings.default_user_id
        ws_dir = Path(record["cwd"])
        repo_name = name or settings.default_project_repo_name
        if any(repo.get("name") == repo_name for repo in record.get("repos", [])):
            raise ValueError(f"Repo already bound to workspace: {repo_name}")

        repo = create_worktree(
            url=url,
            source_dir=Path(settings.workspace_root) / ".sources",
            worktree_path=ws_dir / repo_name,
            branch=branch,
            user_id=owner_id,
        )

        # Persist to workspace record
        record["repos"].append(repo.to_dict())
        record["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._path(ws_id).write_text(json.dumps(record, indent=2))

        return repo

    def create_session_worktree(
        self,
        ws_id: str,
        repo_name: str,
        session_id: str,
        branch: str,
        user_id: Optional[str] = None,
    ) -> RepoInfo:
        record = self.get(ws_id)
        if not record:
            raise ValueError(f"Workspace not found: {ws_id}")
        owner_id = user_id or record.get("user_id") or settings.default_user_id
        repo_record = next(
            (repo for repo in record.get("repos", []) if repo.get("name") == repo_name),
            None,
        )
        if not repo_record:
            raise ValueError(f"Repo not found: {repo_name}")

        worktree_path = Path(record["cwd"]) / ".session-worktrees" / session_id / repo_name
        return create_worktree(
            url=repo_record["url"],
            source_dir=Path(settings.workspace_root) / ".sources",
            worktree_path=worktree_path,
            branch=branch,
            user_id=owner_id,
        )

    def remove_session_worktree(self, repo_path: str | Path) -> None:
        self._remove_worktree(Path(repo_path))

    def pull_all(self, ws_id: str) -> list[dict]:
        record = self.get(ws_id)
        if not record:
            raise ValueError(f"Workspace not found: {ws_id}")
        results = []
        for r in record["repos"]:
            repo_path = Path(record["cwd"]) / r["name"]
            try:
                pull(repo_path, user_id=record.get("user_id"))
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
        s = git_status(repo_path, user_id=record.get("user_id"))
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
        repo = self._find_repo(record, repo_name)
        # Only list branches that exist on the remote — never local-only branches
        # or stale remote-tracking refs from the local clone. A session worktree
        # can only be created from a branch that exists on origin anyway.
        url = repo.get("url") if repo else None
        if not url:
            return []
        return git_remote_branches(url, user_id=record.get("user_id"))

    def _find_repo(self, record: dict, repo_name: str) -> dict | None:
        for repo in record.get("repos", []):
            if repo.get("name") == repo_name:
                return repo
        return None

    def checkout_branch(self, ws_id: str, repo_name: str, branch: str) -> dict:
        record = self.get(ws_id)
        if not record:
            raise ValueError(f"Workspace not found: {ws_id}")
        repo_path = Path(record["cwd"]) / repo_name
        repo_info = git_checkout(repo_path, branch, user_id=record.get("user_id"))
        normalized_branch = normalize_branch_name(repo_info.branch) or branch
        # Update branch in repo record
        for r in record["repos"]:
            if r["name"] == repo_name:
                r["branch"] = normalized_branch
        record["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._path(ws_id).write_text(json.dumps(record, indent=2))
        return {"repo": repo_name, "branch": normalized_branch, "status": "ok"}

workspace_store = WorkspaceStore()
