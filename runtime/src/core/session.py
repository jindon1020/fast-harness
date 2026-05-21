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


class SessionStore:
    """Simple file-based session registry."""

    def __init__(self) -> None:
        self._dir = Path(settings.workspace_root) / ".sessions"
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str) -> Path:
        return self._dir / f"{session_id}.json"

    def create(self, *, workspace_dir: str, metadata: dict) -> str:
        session_id = uuid.uuid4().hex[:12]
        ws = Path(workspace_dir)
        ws.mkdir(parents=True, exist_ok=True)
        (ws / ".session-history").mkdir(parents=True, exist_ok=True)
        record = {
            "session_id": session_id,
            "name": session_id,
            "workspace": str(ws),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_access": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata,
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

    def rename(self, session_id: str, name: str) -> dict:
        record = self.get(session_id)
        if not record:
            raise ValueError(f"Session not found: {session_id}")
        record["name"] = name.strip()
        record["last_access"] = datetime.now(timezone.utc).isoformat()
        self._path(session_id).write_text(json.dumps(record, indent=2), encoding="utf-8")
        return record

    def delete(self, session_id: str) -> None:
        record = self.get(session_id)
        if record:
            history_path = self._history_path(record, session_id)
            if history_path.exists():
                history_path.unlink()
        p = self._path(session_id)
        if p.exists():
            p.unlink()

    def append_message(self, session_id: str, message: dict) -> None:
        record = self.get(session_id)
        if not record:
            raise ValueError(f"Session not found: {session_id}")
        path = self._history_path(record, session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": message,
        }
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def list_messages(self, session_id: str) -> list[dict]:
        record = self.get(session_id)
        if not record:
            raise ValueError(f"Session not found: {session_id}")
        path = self._history_path(record, session_id)
        if not path.exists():
            return []
        messages = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            messages.append(json.loads(line))
        return messages

    def list_all(self) -> list[dict]:
        if not self._dir.exists():
            return []
        records = []
        for f in sorted(self._dir.glob("*.json")):
            records.append(json.loads(f.read_text()))
        return records

    def _history_path(self, record: dict, session_id: str) -> Path:
        return Path(record["workspace"]) / ".session-history" / f"{session_id}.jsonl"


# Global singleton
session_store = SessionStore()
