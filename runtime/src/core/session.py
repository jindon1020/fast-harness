"""
Session persistence layer.

The SDK persists session history to ~/.claude/projects/<encoded-cwd>/*.jsonl.
We track {session_id -> cwd} mapping ourselves so we can resume by session_id.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.config import settings
from src.core.sandbox import get_session_workspace


class SessionStore:
    """Simple file-based session registry."""

    def __init__(self) -> None:
        self._dir = Path(settings.workspace_root) / ".sessions"
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str) -> Path:
        return self._dir / f"{session_id}.json"

    def create(self, workspace_dir: Optional[str] = None) -> str:
        session_id = uuid.uuid4().hex[:12]
        if workspace_dir:
            ws = Path(workspace_dir)
            ws.mkdir(parents=True, exist_ok=True)
        else:
            ws = get_session_workspace(session_id)
        record = {
            "session_id": session_id,
            "workspace": str(ws),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_access": datetime.now(timezone.utc).isoformat(),
            "metadata": {},
        }
        self._path(session_id).write_text(json.dumps(record, indent=2))
        return session_id

    def get(self, session_id: str) -> Optional[dict]:
        p = self._path(session_id)
        if not p.exists():
            return None
        return json.loads(p.read_text())

    def touch(self, session_id: str) -> None:
        record = self.get(session_id)
        if record:
            record["last_access"] = datetime.now(timezone.utc).isoformat()
            self._path(session_id).write_text(json.dumps(record, indent=2))

    def update_metadata(self, session_id: str, meta: dict) -> None:
        record = self.get(session_id)
        if record:
            record["metadata"].update(meta)
            self._path(session_id).write_text(json.dumps(record, indent=2))

    def delete(self, session_id: str) -> None:
        p = self._path(session_id)
        if p.exists():
            p.unlink()

    def list_all(self) -> list[dict]:
        if not self._dir.exists():
            return []
        records = []
        for f in sorted(self._dir.glob("*.json")):
            records.append(json.loads(f.read_text()))
        return records


# Global singleton
session_store = SessionStore()
