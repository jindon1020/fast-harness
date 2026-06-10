"""
Bug-fix pipeline persistence for the runtime UI.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import settings


PIPELINE_STEPS = [
    "intake",
    "root_cause",
    "fix_plan",
    "code_generation",
    "code_review",
    "unit_test",
    "regression",
]

STEP_TITLES = {
    "intake": "问题收集",
    "root_cause": "根因分析",
    "fix_plan": "修复计划",
    "code_generation": "代码生成",
    "code_review": "代码审查",
    "unit_test": "单元测试",
    "regression": "用例回归",
}

TERMINAL_STEP_STATUSES = {"passed", "failed", "skipped", "waiting_approval"}


class BugPipelineStore:
    def __init__(self) -> None:
        self._dir = Path(settings.workspace_root) / ".bug-pipelines"
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, pipeline_id: str) -> Path:
        return self._dir / f"{pipeline_id}.json"

    def create(self, record: dict[str, Any]) -> dict[str, Any]:
        pipeline_id = record.get("pipeline_id") or f"bug-{uuid.uuid4().hex[:10]}"
        now = _now()
        steps = {
            step: {
                "id": step,
                "title": STEP_TITLES[step],
                "status": "pending",
                "attempts": 0,
                "started_at": None,
                "completed_at": None,
                "summary": "",
            }
            for step in PIPELINE_STEPS
        }
        next_record = {
            **record,
            "pipeline_id": pipeline_id,
            "status": record.get("status") or "pending",
            "approval_status": record.get("approval_status") or "not_required",
            "review_retry_count": int(record.get("review_retry_count") or 0),
            "steps": steps,
            "events": [],
            "created_at": now,
            "updated_at": now,
        }
        self._write(next_record)
        return next_record

    def get(self, pipeline_id: str) -> dict[str, Any] | None:
        path = self._path(pipeline_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_all(self) -> list[dict[str, Any]]:
        if not self._dir.exists():
            return []
        records = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(self._dir.glob("*.json"))]
        return sorted(records, key=lambda item: item.get("updated_at", ""), reverse=True)

    def update(self, pipeline_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        record = self.require(pipeline_id)
        record.update(patch)
        record["updated_at"] = _now()
        self._write(record)
        return record

    def set_step(self, pipeline_id: str, step: str, status: str, summary: str = "") -> dict[str, Any]:
        record = self.require(pipeline_id)
        if step not in PIPELINE_STEPS:
            raise ValueError(f"Unknown pipeline step: {step}")
        item = record["steps"][step]
        previous = item.get("status")
        item["status"] = status
        if status == "running" and previous != "running":
            item["attempts"] = int(item.get("attempts") or 0) + 1
            item["started_at"] = _now()
            item["completed_at"] = None
        if status in TERMINAL_STEP_STATUSES:
            item["completed_at"] = _now()
        if summary:
            item["summary"] = summary
        record["status"] = _pipeline_status(record)
        record["updated_at"] = _now()
        self._write(record)
        return record

    def append_event(self, pipeline_id: str, event: dict[str, Any]) -> dict[str, Any]:
        record = self.require(pipeline_id)
        record.setdefault("events", []).append({"timestamp": _now(), **event})
        record["updated_at"] = _now()
        self._write(record)
        return record

    def require(self, pipeline_id: str) -> dict[str, Any]:
        record = self.get(pipeline_id)
        if not record:
            raise ValueError(f"Bug pipeline not found: {pipeline_id}")
        return record

    def _write(self, record: dict[str, Any]) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path(record["pipeline_id"]).write_text(
            json.dumps(record, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def _pipeline_status(record: dict[str, Any]) -> str:
    steps = record.get("steps") or {}
    if any(step.get("status") == "running" for step in steps.values()):
        return "running"
    if steps.get("fix_plan", {}).get("status") == "waiting_approval":
        return "waiting_approval"
    if any(step.get("status") == "failed" for step in steps.values()):
        return "failed"
    if steps and all(step.get("status") == "passed" for step in steps.values()):
        return "passed"
    return "pending"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


bug_pipeline_store = BugPipelineStore()
