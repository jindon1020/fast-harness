"""
REST API routes for the fast-harness runtime service.
"""

import base64
import json
import logging
import re
import uuid
import asyncio
import urllib.request
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Cookie, Header, HTTPException
from sse_starlette.sse import EventSourceResponse
from starlette.responses import JSONResponse, Response

from src.api.schemas import (
    AnswerRequest,
    AnswerResponse,
    BugPipelineApprovalRequest,
    BugPipelineCreateRequest,
    BugPipelineListResponse,
    BugPipelineResponse,
    BugPipelineStepRunRequest,
    BugPipelineTerminateRequest,
    CurrentUserResponse,
    FeedbackRequest,
    FeedbackResponse,
    GitActionResponse,
    GitCommitMessageResponse,
    GitCommitRequest,
    LoginRequest,
    LoginResponse,
    QueryRequest,
    RenameRequest,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionInfo,
    SessionListResponse,
    UsageStatsResponse,
    UserListResponse,
    WorkspaceCreateRequest,
    WorkspaceRepoAddRequest,
    WorkspaceResponse,
    WorkspaceListResponse,
    RepositoryListResponse,
    RepoStatusResponse,
    SessionDiffResponse,
    CapabilityResponse,
    HealthResponse,
)
from src.config import settings
from src.core.auth import (
    SESSION_COOKIE_NAME,
    SESSION_TTL_SECONDS,
    authenticate_user,
    create_session_token,
    public_user,
    verify_session_token,
)
from src.core.git import (
    checkout as git_checkout,
    commit_all as git_commit_all,
    commit_message_context,
    push as git_push,
    remote_branches,
    session_diff as git_session_diff,
    status as git_status,
)
from src.core.agent import generate_commit_message, provide_answers, run_query_stream, resolve_session_repo_path
from src.core.bug_pipeline import PIPELINE_STEPS, bug_pipeline_store
from src.core.session import session_store
from src.core.workspace import workspace_store
from src.harness.registry import get_capabilities

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")
FEEDBACK_PATH = Path(__file__).resolve().parents[2] / "feedback.md"
SKIPPABLE_BUG_STEPS = {"code_review", "unit_test", "regression"}
STEP_COMPLETE_STATUSES = {"passed", "skipped"}

UserHeader = Annotated[str | None, Header(alias="X-User-Id")]
SessionCookie = Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)]


def _current_user_id(
    x_user_id: str | None = None,
    session_token: str | None = None,
) -> str:
    cookie_user_id = verify_session_token(session_token)
    requested = cookie_user_id or (x_user_id.strip() if isinstance(x_user_id, str) else "")
    user_id = requested or settings.default_user_id
    try:
        settings.get_user(user_id)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return user_id


def _record_user_id(record: dict) -> str:
    return record.get("user_id") or record.get("metadata", {}).get("user_id") or settings.default_user_id


def _ensure_owned(record: dict | None, user_id: str, not_found: str):
    if not record or _record_user_id(record) != user_id:
        raise HTTPException(status_code=404, detail=not_found)
    return record


def _ensure_admin(user_id: str) -> None:
    if not settings.is_admin(user_id):
        raise HTTPException(status_code=403, detail="Admin role required")


def _append_feedback(user_id: str, session_id: str, body: FeedbackRequest) -> Path:
    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = _format_feedback_entry(user_id, session_id, body)
    if not FEEDBACK_PATH.exists():
        FEEDBACK_PATH.write_text("# Feedback\n\n", encoding="utf-8")
    content = FEEDBACK_PATH.read_text(encoding="utf-8")
    heading = f"## {user_id}"
    if heading not in content:
        next_content = content.rstrip() + f"\n\n{heading}\n\n{entry}\n"
    else:
        start = content.index(heading)
        next_heading = content.find("\n## ", start + len(heading))
        insert_at = len(content) if next_heading == -1 else next_heading + 1
        next_content = content[:insert_at].rstrip() + f"\n\n{entry}\n\n" + content[insert_at:].lstrip()
    FEEDBACK_PATH.write_text(next_content, encoding="utf-8")
    return FEEDBACK_PATH


def _format_feedback_entry(user_id: str, session_id: str, body: FeedbackRequest) -> str:
    from datetime import datetime, timezone

    timestamp = datetime.now(timezone.utc).isoformat()
    feedback = body.feedback.strip()
    excerpt = (body.message_excerpt or "").strip()
    lines = [
        f"### {timestamp}",
        "",
        f"- user_id: `{user_id}`",
        f"- session_id: `{session_id}`",
        "",
        "Feedback:",
        "",
        _markdown_quote(feedback),
    ]
    if excerpt:
        lines.extend(["", "AI message excerpt:", "", _markdown_quote(excerpt)])
    return "\n".join(lines)


def _markdown_quote(text: str) -> str:
    return "\n".join(f"> {line}" if line else ">" for line in text.splitlines())


def _usage_stats() -> dict:
    stats = {
        user["id"]: {
            "user_id": user["id"],
            "name": user["name"],
            "workspace_count": 0,
            "session_count": 0,
            "conversation_count": 0,
            "result_count": 0,
            "command_count": 0,
            "feedback_count": 0,
            "last_active": None,
            "commands": {},
        }
        for user in settings.enabled_users
    }

    def user_stats(user_id: str) -> dict:
        if user_id not in stats:
            stats[user_id] = {
                "user_id": user_id,
                "name": user_id,
                "workspace_count": 0,
                "session_count": 0,
                "conversation_count": 0,
                "result_count": 0,
                "command_count": 0,
                "feedback_count": 0,
                "last_active": None,
                "commands": {},
            }
        return stats[user_id]

    for workspace in workspace_store.list_all():
        user_stats(_record_user_id(workspace))["workspace_count"] += 1

    for session in session_store.list_all():
        user_id = _record_user_id(session)
        bucket = user_stats(user_id)
        bucket["session_count"] += 1
        _set_last_active(bucket, session.get("last_access") or session.get("created_at"))
        for entry in _safe_session_messages(session):
            timestamp = entry.get("timestamp")
            message = entry.get("message") or entry
            if message.get("type") == "user":
                bucket["conversation_count"] += 1
                _set_last_active(bucket, timestamp)
                command = _extract_command(message.get("prompt", ""))
                if command:
                    bucket["command_count"] += 1
                    bucket["commands"][command] = bucket["commands"].get(command, 0) + 1
            elif message.get("type") == "result":
                bucket["result_count"] += 1
                _set_last_active(bucket, timestamp)

    for user_id, count in _feedback_counts_by_user().items():
        user_stats(user_id)["feedback_count"] = count

    users = []
    for item in stats.values():
        commands = [
            {"command": command, "count": count}
            for command, count in sorted(item["commands"].items(), key=lambda kv: (-kv[1], kv[0]))
        ]
        users.append({**item, "commands": commands})

    users.sort(key=lambda item: (-item["conversation_count"], -item["command_count"], item["user_id"]))
    totals = {
        "workspace_count": sum(item["workspace_count"] for item in users),
        "session_count": sum(item["session_count"] for item in users),
        "conversation_count": sum(item["conversation_count"] for item in users),
        "result_count": sum(item["result_count"] for item in users),
        "command_count": sum(item["command_count"] for item in users),
        "feedback_count": sum(item["feedback_count"] for item in users),
    }
    return {"users": users, "totals": totals}


def _safe_session_messages(session: dict) -> list[dict]:
    try:
        return session_store.list_messages(session["session_id"])
    except Exception as exc:
        logger.warning("Failed to read session messages for %s: %s", session.get("session_id"), exc)
        return []


def _extract_command(prompt: str) -> str | None:
    match = re.match(r"^\s*/([A-Za-z0-9_-]+)", prompt or "")
    return match.group(1) if match else None


def _set_last_active(bucket: dict, timestamp: str | None) -> None:
    if timestamp and (not bucket["last_active"] or timestamp > bucket["last_active"]):
        bucket["last_active"] = timestamp


def _feedback_counts_by_user() -> dict[str, int]:
    if not FEEDBACK_PATH.exists():
        return {}
    counts: dict[str, int] = {}
    current_user: str | None = None
    for line in FEEDBACK_PATH.read_text(encoding="utf-8").splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            current_user = heading.group(1)
            counts.setdefault(current_user, 0)
            continue
        if current_user and line.startswith("### "):
            counts[current_user] = counts.get(current_user, 0) + 1
    return counts


# ═══════════════════════ Health ═══════════════════════

@router.get("/healthz", response_model=HealthResponse)
async def health():
    harness_path = settings.resolved_harness_path
    return HealthResponse(
        status="ok",
        version="0.1.0",
        harness_loaded=harness_path.exists(),
    )


# ═══════════════════════ Capabilities ═══════════════════════

@router.get("/capabilities", response_model=CapabilityResponse)
async def capabilities():
    caps = get_capabilities()
    return CapabilityResponse(**caps)


# ═══════════════════════ Registered repositories ═══════════════════════

@router.get("/users", response_model=UserListResponse)
async def list_users():
    return UserListResponse(
        users=[public_user(user) for user in settings.enabled_users],
        default_user_id=settings.default_user_id,
    )


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, response: Response):
    user = authenticate_user(body.user_id, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    response.set_cookie(
        SESSION_COOKIE_NAME,
        create_session_token(user["id"]),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
    )
    return LoginResponse(status="ok", user=public_user(user))


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"status": "ok"}


@router.get("/me", response_model=CurrentUserResponse)
async def me(session_token: SessionCookie = None):
    user_id = verify_session_token(session_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return CurrentUserResponse(user=public_user(settings.get_user(user_id)))


@router.get("/usage-stats", response_model=UsageStatsResponse)
async def usage_stats(x_user_id: UserHeader = None):
    _ensure_admin(_current_user_id(x_user_id))
    return UsageStatsResponse(**_usage_stats())


@router.get("/repositories", response_model=RepositoryListResponse)
async def list_repositories():
    return RepositoryListResponse(repositories=settings.enabled_repositories)


@router.get("/repositories/{repo_key}/branches")
async def repository_branches(repo_key: str, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    try:
        repo = settings.get_repository(repo_key)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    branches = remote_branches(repo["url"], user_id=user_id)
    return {"branches": branches or [repo["default_branch"]]}


# ═══════════════════════ Bug fix pipelines ═══════════════════════

@router.post("/bug-pipelines", response_model=BugPipelineResponse, status_code=201)
async def create_bug_pipeline(body: BugPipelineCreateRequest, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    _ensure_developer_user(body.reviewer_id)
    target_branch = _normalize_feature_branch(body.target_branch)
    git_user_id = body.reviewer_id if settings.is_reporter(user_id) else user_id
    repo_contexts = _build_bug_repo_contexts(body, target_branch)
    primary_context = repo_contexts[0]
    repo = _repo_spec_from_config(primary_context["repo_key"], target_branch)
    _ensure_remote_feature_branch(repo["url"], target_branch, git_user_id)
    for context in repo_contexts[1:]:
        _ensure_remote_branch(context["url"], context["branch"], git_user_id)

    pipeline_id = f"bug-{uuid.uuid4().hex[:10]}"
    workspace_rec = workspace_store.create(
        f"BugFix {pipeline_id}",
        repositories=[
            {
                "key": context["repo_key"],
                "name": context["repo_name"],
                "url": context["url"],
                "branch": context["branch"],
                "install_harness": False,
            }
            for context in repo_contexts
        ],
        user_id=user_id,
        git_user_id=git_user_id,
    )
    sid = uuid.uuid4().hex[:12]
    session_repos = []
    try:
        session_repo = workspace_store.create_session_worktree(
            workspace_rec["workspace_id"],
            primary_context["repo_name"],
            sid,
            target_branch,
            user_id=user_id,
            git_user_id=git_user_id,
            install_harness=True,
        )
        session_repos.append(session_repo)
        for context in repo_contexts[1:]:
            related_repo = workspace_store.create_session_worktree(
                workspace_rec["workspace_id"],
                context["repo_name"],
                sid,
                context["branch"],
                user_id=user_id,
                git_user_id=git_user_id,
                install_harness=False,
            )
            session_repos.append(related_repo)
            context["local_path"] = str(related_repo.local_path)
        primary_context["local_path"] = str(session_repo.local_path)
        session_workspace = Path(workspace_rec["cwd"]) / ".session-worktrees" / sid
        session_store.create(
            workspace_dir=str(session_workspace),
            metadata={
                "user_id": user_id,
                "workspace_id": workspace_rec["workspace_id"],
                "repo_name": primary_context["repo_name"],
                "branch": target_branch,
                "target_branch": target_branch,
                "bug_pipeline_id": pipeline_id,
                "git_user_id": git_user_id,
                "session_repo_path": str(session_repo.local_path),
                "related_repo_paths": {
                    context["repo_name"]: context.get("local_path")
                    for context in repo_contexts[1:]
                },
            },
            session_id=sid,
            user_id=user_id,
        )
    except Exception:
        for created_repo in session_repos:
            workspace_store.remove_session_worktree(created_repo.local_path)
        workspace_store.delete(workspace_rec["workspace_id"])
        raise

    artifact_dir = Path(session_repo.local_path) / ".ai" / "dev-fix" / pipeline_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    screenshot_attachments = _save_bug_screenshots(body, artifact_dir, Path(session_repo.local_path))
    record = bug_pipeline_store.create(
        {
            "pipeline_id": pipeline_id,
            "code_approval_status": "not_required",
            "user_id": user_id,
            "reviewer_id": body.reviewer_id,
            "repo_key": body.repo_key,
            "repo_name": primary_context["repo_name"],
            "repo_contexts": _public_repo_contexts(repo_contexts),
            "workspace_id": workspace_rec["workspace_id"],
            "session_id": sid,
            "target_branch": target_branch,
            "bugfix_branch": target_branch,
            "git_user_id": git_user_id,
            "namespace": body.namespace.strip(),
            "request_id": primary_context.get("correlation_id_value") or _clean_optional(body.request_id),
            "affected_api": body.affected_api.strip(),
            "problem_description": body.problem_description.strip(),
            "expected_result": body.expected_result.strip(),
            "actual_result": body.actual_result.strip(),
            "screenshot_notes": _clean_optional(body.screenshot_notes),
            "screenshot_attachments": screenshot_attachments,
            "occurred_at": _clean_optional(body.occurred_at),
            "affected_data": _clean_optional(body.affected_data),
            "regression_curl": _clean_optional(body.regression_curl),
            "extra_context": _clean_optional(body.extra_context),
            "artifact_dir": str(artifact_dir.relative_to(session_repo.local_path)),
        }
    )
    _write_bug_report(record, Path(session_repo.local_path))
    bug_pipeline_store.set_step(pipeline_id, "intake", "passed", "已生成结构化 bug_report.md")
    bug_pipeline_store.append_event(
        pipeline_id,
        {"type": "created", "message": f"Pipeline will modify and push target branch {target_branch}"},
    )
    asyncio.create_task(_start_bug_pipeline_step(pipeline_id, "root_cause"))
    return BugPipelineResponse(**bug_pipeline_store.require(pipeline_id))


@router.get("/bug-pipelines", response_model=BugPipelineListResponse)
async def list_bug_pipelines(x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    records = [
        record
        for record in bug_pipeline_store.list_all()
        if _can_view_pipeline(record, user_id)
    ]
    return BugPipelineListResponse(pipelines=[BugPipelineResponse(**record) for record in records])


@router.get("/bug-pipelines/{pipeline_id}", response_model=BugPipelineResponse)
async def get_bug_pipeline(pipeline_id: str, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    record = _ensure_pipeline_visible(pipeline_id, user_id)
    return BugPipelineResponse(**record)


@router.patch("/bug-pipelines/{pipeline_id}", response_model=BugPipelineResponse)
async def rename_bug_pipeline(pipeline_id: str, body: RenameRequest, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    _ensure_pipeline_visible(pipeline_id, user_id)
    record = bug_pipeline_store.rename(pipeline_id, body.name)
    bug_pipeline_store.append_event(
        pipeline_id,
        {"type": "rename", "user_id": user_id, "name": body.name.strip()},
    )
    return BugPipelineResponse(**bug_pipeline_store.require(pipeline_id))


@router.delete("/bug-pipelines/{pipeline_id}")
async def delete_bug_pipeline(pipeline_id: str, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    record = _ensure_pipeline_visible(pipeline_id, user_id)
    if _is_query_active(record["session_id"]):
        raise HTTPException(status_code=409, detail="Pipeline already has a running step")
    session_store.delete(record["session_id"])
    bug_pipeline_store.delete(pipeline_id)
    return {"status": "deleted", "pipeline_id": pipeline_id}


@router.get("/bug-pipelines/{pipeline_id}/artifacts/{artifact_name}")
async def get_bug_pipeline_artifact(pipeline_id: str, artifact_name: str, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    record = _ensure_pipeline_visible(pipeline_id, user_id)
    allowed = {
        "bug_report.md",
        "diagnosis.md",
        "fix_plan.md",
        "changed_files.txt",
        "implementation_notes.md",
        "review_feedback.md",
        "unit_test_results.md",
        "regression_results.md",
    }
    if artifact_name not in allowed:
        raise HTTPException(status_code=404, detail="Artifact not found")
    repo_path = resolve_session_repo_path(record["session_id"]).resolve()
    target = _artifact_path(record, repo_path, artifact_name).resolve()
    if repo_path != target and repo_path not in target.parents:
        raise HTTPException(status_code=403, detail="Path traversal denied")
    if not target.exists() or not target.is_file():
        return {"pipeline_id": pipeline_id, "artifact": artifact_name, "content": ""}
    return {"pipeline_id": pipeline_id, "artifact": artifact_name, "content": target.read_text(encoding="utf-8")}


@router.get("/bug-pipelines/{pipeline_id}/screenshots/{filename}")
async def get_bug_pipeline_screenshot(pipeline_id: str, filename: str, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    record = _ensure_pipeline_visible(pipeline_id, user_id)
    attachment = next(
        (
            item
            for item in record.get("screenshot_attachments") or []
            if Path(str(item.get("path", ""))).name == filename
        ),
        None,
    )
    if not attachment:
        raise HTTPException(status_code=404, detail="Screenshot not found")
    repo_path = resolve_session_repo_path(record["session_id"]).resolve()
    target = (repo_path / attachment["path"]).resolve()
    if repo_path != target and repo_path not in target.parents:
        raise HTTPException(status_code=403, detail="Path traversal denied")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Screenshot not found")
    return Response(content=target.read_bytes(), media_type=attachment.get("mime_type") or "application/octet-stream")


@router.post("/bug-pipelines/{pipeline_id}/steps/{step}/run", response_model=BugPipelineResponse)
async def run_bug_pipeline_step(
    pipeline_id: str,
    step: str,
    body: BugPipelineStepRunRequest | None = None,
    x_user_id: UserHeader = None,
):
    user_id = _current_user_id(x_user_id)
    record = _ensure_pipeline_visible(pipeline_id, user_id)
    if step not in PIPELINE_STEPS:
        raise HTTPException(status_code=404, detail=f"Unknown pipeline step: {step}")
    if step == "intake":
        return BugPipelineResponse(**record)
    if _is_query_active(record["session_id"]):
        raise HTTPException(status_code=409, detail="Pipeline already has a running step")
    _ensure_step_can_run(record, step)
    updated = await _start_bug_pipeline_step(pipeline_id, step, body.note if body else None)
    return BugPipelineResponse(**updated)


@router.post("/bug-pipelines/{pipeline_id}/steps/{step}/skip", response_model=BugPipelineResponse)
async def skip_bug_pipeline_step(
    pipeline_id: str,
    step: str,
    body: BugPipelineStepRunRequest | None = None,
    x_user_id: UserHeader = None,
):
    user_id = _current_user_id(x_user_id)
    record = _ensure_pipeline_visible(pipeline_id, user_id)
    _ensure_pipeline_terminator(record, user_id)
    if step not in SKIPPABLE_BUG_STEPS:
        raise HTTPException(status_code=400, detail="Only code review, unit test, and regression steps can be skipped")
    _ensure_step_can_run(record, step)
    current_status = record.get("steps", {}).get(step, {}).get("status")
    if current_status in STEP_COMPLETE_STATUSES:
        raise HTTPException(status_code=409, detail=f"Step is already complete: {step}")
    if _is_query_active(record["session_id"]):
        running_step = _running_bug_step(record)
        if running_step != step:
            raise HTTPException(status_code=409, detail="Pipeline already has another running step")
        active = _active_queries.get(record["session_id"])
        if active and active.task and not active.task.done():
            active.task.cancel()
    reason = _clean_optional(body.note if body else None) or "人工跳过该阶段"
    updated = bug_pipeline_store.set_step(pipeline_id, step, "skipped", reason)
    bug_pipeline_store.append_event(
        pipeline_id,
        {"type": "step_skipped", "step": step, "user_id": user_id, "reason": reason},
    )
    next_step = _next_auto_step(step)
    if next_step:
        refreshed = bug_pipeline_store.require(pipeline_id)
        if refreshed.get("steps", {}).get(next_step, {}).get("status") == "pending":
            asyncio.create_task(_start_bug_pipeline_step(pipeline_id, next_step))
    return BugPipelineResponse(**bug_pipeline_store.require(pipeline_id))


@router.post("/bug-pipelines/{pipeline_id}/approval", response_model=BugPipelineResponse)
async def approve_bug_pipeline(
    pipeline_id: str,
    body: BugPipelineApprovalRequest,
    x_user_id: UserHeader = None,
):
    user_id = _current_user_id(x_user_id)
    record = _ensure_pipeline_visible(pipeline_id, user_id)
    _ensure_pipeline_approver(record, user_id)
    if record.get("steps", {}).get("fix_plan", {}).get("status") != "waiting_approval":
        raise HTTPException(status_code=409, detail="Pipeline is not waiting for plan approval")
    approval_status = "approved" if body.approved else "rejected"
    bug_pipeline_store.update(
        pipeline_id,
        {
            "approval_status": approval_status,
            "approval_comment": _clean_optional(body.comment),
            "approved_by": user_id,
        },
    )
    if body.approved:
        updated = bug_pipeline_store.set_step(pipeline_id, "fix_plan", "passed", "研发已审批通过修复计划")
        asyncio.create_task(_start_bug_pipeline_step(pipeline_id, "code_generation"))
    else:
        updated = bug_pipeline_store.set_step(pipeline_id, "fix_plan", "failed", "研发已拒绝修复计划")
    bug_pipeline_store.append_event(
        pipeline_id,
        {"type": "approval", "approved": body.approved, "user_id": user_id, "comment": body.comment or ""},
    )
    return BugPipelineResponse(**bug_pipeline_store.require(pipeline_id))


@router.post("/bug-pipelines/{pipeline_id}/terminate", response_model=BugPipelineResponse)
async def terminate_bug_pipeline(
    pipeline_id: str,
    body: BugPipelineTerminateRequest | None = None,
    x_user_id: UserHeader = None,
):
    user_id = _current_user_id(x_user_id)
    record = _ensure_pipeline_visible(pipeline_id, user_id)
    _ensure_pipeline_terminator(record, user_id)
    if record.get("status") in {"passed", "failed", "terminated"}:
        raise HTTPException(status_code=409, detail="Pipeline is already finished")
    active = _active_queries.get(record["session_id"])
    if active and active.task and not active.task.done():
        active.task.cancel()
    reason = _clean_optional(body.reason if body else None) or "测试确认无需继续修复"
    updated = bug_pipeline_store.terminate(pipeline_id, user_id, reason)
    bug_pipeline_store.append_event(
        pipeline_id,
        {"type": "terminated", "user_id": user_id, "reason": reason},
    )
    return BugPipelineResponse(**bug_pipeline_store.require(pipeline_id))


@router.post("/bug-pipelines/{pipeline_id}/code-approval", response_model=BugPipelineResponse)
async def approve_bug_pipeline_code(
    pipeline_id: str,
    body: BugPipelineApprovalRequest,
    x_user_id: UserHeader = None,
):
    user_id = _current_user_id(x_user_id)
    record = _ensure_pipeline_visible(pipeline_id, user_id)
    _ensure_pipeline_developer_operator(record, user_id)
    _ensure_pipeline_code_ready(record)
    code_approval_status = "approved" if body.approved else "rejected"
    updated = bug_pipeline_store.update(
        pipeline_id,
        {
            "code_approval_status": code_approval_status,
            "code_approval_comment": _clean_optional(body.comment),
            "code_approved_by": user_id,
        },
    )
    bug_pipeline_store.append_event(
        pipeline_id,
        {"type": "code_approval", "approved": body.approved, "user_id": user_id, "comment": body.comment or ""},
    )
    return BugPipelineResponse(**updated)


@router.get("/bug-pipelines/{pipeline_id}/git/commit-message", response_model=GitCommitMessageResponse)
async def suggest_bug_pipeline_commit_message(pipeline_id: str, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    record = _ensure_pipeline_visible(pipeline_id, user_id)
    _ensure_pipeline_developer_operator(record, user_id)
    _ensure_pipeline_code_ready(record)
    if _is_query_active(record["session_id"]):
        raise HTTPException(status_code=409, detail="Pipeline already has a running step")
    repo_path = resolve_session_repo_path(record["session_id"]).resolve()
    try:
        context = commit_message_context(repo_path)
        if not context:
            return GitCommitMessageResponse(message=_fallback_bug_commit_message(record), generated=False)
        message = await generate_commit_message(repo_path, context)
        return GitCommitMessageResponse(message=message, generated=True)
    except RuntimeError as e:
        logger.warning("AI commit message generation failed for bug pipeline %s: %s", pipeline_id, e)
        return GitCommitMessageResponse(message=_fallback_bug_commit_message(record), generated=False)


@router.post("/bug-pipelines/{pipeline_id}/git/commit", response_model=GitActionResponse)
async def commit_bug_pipeline_changes(
    pipeline_id: str,
    body: GitCommitRequest,
    x_user_id: UserHeader = None,
):
    user_id = _current_user_id(x_user_id)
    record = _ensure_pipeline_visible(pipeline_id, user_id)
    _ensure_pipeline_developer_operator(record, user_id)
    _ensure_pipeline_code_ready(record)
    _ensure_pipeline_code_approved(record)
    if _is_query_active(record["session_id"]):
        raise HTTPException(status_code=409, detail="Pipeline already has a running step")
    try:
        repo_path = resolve_session_repo_path(record["session_id"]).resolve()
        git_user_id = record.get("git_user_id") or record.get("reviewer_id") or user_id
        result = git_commit_all(repo_path, body.message, user_id=git_user_id)
        bug_pipeline_store.append_event(
            pipeline_id,
            {"type": "git_commit", "user_id": user_id, "status": result.status, "branch": result.branch},
        )
        return GitActionResponse(**result.to_dict())
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bug-pipelines/{pipeline_id}/git/push", response_model=GitActionResponse)
async def push_bug_pipeline_changes(pipeline_id: str, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    record = _ensure_pipeline_visible(pipeline_id, user_id)
    _ensure_pipeline_developer_operator(record, user_id)
    _ensure_pipeline_code_ready(record)
    _ensure_pipeline_code_approved(record)
    if _is_query_active(record["session_id"]):
        raise HTTPException(status_code=409, detail="Pipeline already has a running step")
    try:
        repo_path = resolve_session_repo_path(record["session_id"]).resolve()
        git_user_id = record.get("git_user_id") or record.get("reviewer_id") or user_id
        result = git_push(repo_path, branch=record.get("target_branch"), user_id=git_user_id)
        bug_pipeline_store.append_event(
            pipeline_id,
            {"type": "git_push", "user_id": user_id, "status": result.status, "branch": result.branch},
        )
        return GitActionResponse(**result.to_dict())
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bug-pipelines/{pipeline_id}/stream")
async def stream_bug_pipeline(pipeline_id: str, since: int = -1, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    record = _ensure_pipeline_visible(pipeline_id, user_id)
    return EventSourceResponse(_query_event_stream(record["session_id"], since=since))


def _ensure_known_user(user_id: str) -> None:
    try:
        settings.get_user(user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


def _ensure_developer_user(user_id: str) -> None:
    try:
        if settings.is_developer(user_id):
            return
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    raise HTTPException(status_code=400, detail="审批研发必须是 member 或 admin 角色")


def _normalize_feature_branch(branch: str) -> str:
    value = branch.strip()
    for prefix in ("origin/", "refs/heads/"):
        if value.startswith(prefix):
            value = value[len(prefix):]
    if not value:
        raise HTTPException(status_code=400, detail="目标 feature 分支不能为空")
    if not value.startswith("feature/"):
        raise HTTPException(status_code=400, detail="目标修复分支必须是 feature/* 远端分支")
    return value


def _ensure_remote_feature_branch(repo_url: str, branch: str, user_id: str) -> None:
    branches = remote_branches(repo_url, user_id=user_id)
    if branch not in branches:
        raise HTTPException(status_code=400, detail=f"目标 feature 分支不存在于远端: {branch}")


def _ensure_remote_branch(repo_url: str, branch: str, user_id: str) -> None:
    branches = remote_branches(repo_url, user_id=user_id)
    if branch not in branches:
        raise HTTPException(status_code=400, detail=f"关联仓库分支不存在于远端: {branch}")


def _build_bug_repo_contexts(body: BugPipelineCreateRequest, target_branch: str) -> list[dict]:
    contexts = body.repo_contexts or []
    by_repo_key = {context.repo_key: context for context in contexts}
    primary_input = by_repo_key.get(body.repo_key)
    primary_correlation_name = _clean_optional(primary_input.correlation_id_name if primary_input else None) or "request_id"
    primary_correlation_value = _clean_optional(primary_input.correlation_id_value if primary_input else None) or _clean_optional(body.request_id)
    try:
        primary_repo = settings.get_repository(body.repo_key)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    result = [
        {
            "repo_key": primary_repo["key"],
            "repo_name": primary_repo["name"],
            "url": primary_repo["url"],
            "branch": target_branch,
            "role": "fix",
            "correlation_id_name": primary_correlation_name,
            "correlation_id_value": primary_correlation_value,
            "note": _clean_optional(primary_input.note if primary_input else None),
        }
    ]
    seen = {body.repo_key}
    for context in contexts:
        if context.repo_key in seen:
            continue
        try:
            repo = settings.get_repository(context.repo_key)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        branch = _clean_optional(context.branch) or repo["default_branch"]
        result.append(
            {
                "repo_key": repo["key"],
                "repo_name": repo["name"],
                "url": repo["url"],
                "branch": branch,
                "role": "observe",
                "correlation_id_name": _clean_optional(context.correlation_id_name),
                "correlation_id_value": _clean_optional(context.correlation_id_value),
                "note": _clean_optional(context.note),
            }
        )
        seen.add(context.repo_key)
    return result


def _public_repo_contexts(contexts: list[dict]) -> list[dict]:
    return [
        {
            "repo_key": context["repo_key"],
            "repo_name": context["repo_name"],
            "branch": context["branch"],
            "role": context["role"],
            "correlation_id_name": context.get("correlation_id_name"),
            "correlation_id_value": context.get("correlation_id_value"),
            "note": context.get("note"),
            "local_path": context.get("local_path"),
        }
        for context in contexts
    ]


def _branch_slug(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", text.lower()).strip(".-")
    return (slug[:32].strip(".-") or "fix")


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _can_view_pipeline(record: dict, user_id: str) -> bool:
    return (
        record.get("user_id") == user_id
        or record.get("reviewer_id") == user_id
        or settings.is_admin(user_id)
    )


def _ensure_pipeline_visible(pipeline_id: str, user_id: str) -> dict:
    try:
        record = bug_pipeline_store.require(pipeline_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if not _can_view_pipeline(record, user_id):
        raise HTTPException(status_code=404, detail="Bug pipeline not found")
    return record


def _ensure_pipeline_approver(record: dict, user_id: str) -> None:
    if not settings.is_developer(user_id):
        raise HTTPException(status_code=403, detail="Only developer roles can approve this plan")
    if record.get("reviewer_id") == user_id or settings.is_admin(user_id):
        return
    raise HTTPException(status_code=403, detail="Only the assigned reviewer or admin can approve this plan")


def _ensure_pipeline_terminator(record: dict, user_id: str) -> None:
    if record.get("user_id") == user_id or record.get("reviewer_id") == user_id or settings.is_admin(user_id):
        return
    raise HTTPException(status_code=403, detail="Only the reporter, assigned reviewer, or admin can terminate this pipeline")


def _ensure_pipeline_developer_operator(record: dict, user_id: str) -> None:
    if not settings.is_developer(user_id):
        raise HTTPException(status_code=403, detail="Only developer roles can operate bugfix code")
    if record.get("reviewer_id") == user_id or settings.is_admin(user_id):
        return
    raise HTTPException(status_code=403, detail="Only the assigned reviewer or admin can operate this bugfix code")


def _ensure_pipeline_code_ready(record: dict) -> None:
    if record.get("status") == "terminated":
        raise HTTPException(status_code=409, detail="Bug pipeline has been terminated")
    if record.get("steps", {}).get("regression", {}).get("status") not in STEP_COMPLETE_STATUSES:
        raise HTTPException(status_code=409, detail="Bug pipeline must pass regression before code approval")


def _ensure_pipeline_code_approved(record: dict) -> None:
    if record.get("code_approval_status") != "approved":
        raise HTTPException(status_code=409, detail="Bugfix code must be approved before commit or push")


def _pipeline_session(record: dict) -> dict:
    session = session_store.get(record["session_id"])
    if not session:
        raise HTTPException(status_code=404, detail="Pipeline session not found")
    return session


def _ensure_step_can_run(record: dict, step: str) -> None:
    if record.get("status") == "terminated":
        raise HTTPException(status_code=409, detail="Pipeline has been terminated")
    steps = record.get("steps") or {}
    index = PIPELINE_STEPS.index(step)
    for previous in PIPELINE_STEPS[1:index]:
        if steps.get(previous, {}).get("status") not in STEP_COMPLETE_STATUSES:
            raise HTTPException(status_code=409, detail=f"Previous step is not passed: {previous}")
    if step == "code_generation" and record.get("approval_status") != "approved":
        raise HTTPException(status_code=409, detail="Fix plan must be approved before code generation")
    if step == "code_generation" and int(record.get("review_retry_count") or 0) >= 3:
        raise HTTPException(status_code=409, detail="Code review retry limit reached")


def _running_bug_step(record: dict) -> str | None:
    for step, info in (record.get("steps") or {}).items():
        if info.get("status") == "running":
            return step
    return None


async def _start_bug_pipeline_step(pipeline_id: str, step: str, note: str | None = None) -> dict:
    record = bug_pipeline_store.require(pipeline_id)
    if step not in PIPELINE_STEPS:
        raise HTTPException(status_code=404, detail=f"Unknown pipeline step: {step}")
    if _is_query_active(record["session_id"]):
        return record
    _ensure_step_can_run(record, step)
    _checkout_session_branch(_pipeline_session(record))
    prompt = _bug_pipeline_step_prompt(record, step, note)
    query_body = QueryRequest(prompt=prompt, max_turns=settings.default_max_turns)
    active = _ensure_query_started(record["session_id"], query_body)
    updated = bug_pipeline_store.set_step(pipeline_id, step, "running")
    asyncio.create_task(_finalize_bug_pipeline_step(pipeline_id, step, active.task))
    return updated


def _artifact_path(record: dict, repo_path: Path, name: str) -> Path:
    return repo_path / record["artifact_dir"] / name


def _write_bug_report(record: dict, repo_path: Path) -> None:
    path = _artifact_path(record, repo_path, "bug_report.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Bug Report: {record['pipeline_id']}",
        "",
        "## 基本信息",
        f"- pipeline_id: `{record['pipeline_id']}`",
        f"- namespace: `{record['namespace']}`",
        f"- 主修复仓库: `{record['repo_name']}`",
        f"- target_branch: `{record['target_branch']}`",
        f"- push_branch: `{record['target_branch']}`",
        f"- reviewer_id: `{record['reviewer_id']}`",
    ]
    repo_contexts = record.get("repo_contexts") or []
    if repo_contexts:
        lines.extend(["", "## 仓库上下文"])
        for context in repo_contexts:
            correlation_name = context.get("correlation_id_name") or "关联 ID"
            correlation_value = context.get("correlation_id_value") or "未提供"
            local_path = context.get("local_path") or ""
            lines.append(
                f"- `{context.get('repo_name')}` ({context.get('role')}): "
                f"branch `{context.get('branch')}`, {correlation_name} `{correlation_value}`"
                + (f", path `{local_path}`" if local_path else "")
            )
            if context.get("note"):
                lines.append(f"  - 说明: {context['note']}")
    lines.extend(
        [
            "",
            "## 问题描述",
            record["problem_description"],
            "",
            "## 涉及接口",
            record["affected_api"],
            "",
            "## 预期结果",
            record["expected_result"],
            "",
            "## 实际结果",
            record["actual_result"],
        ]
    )
    optional_fields = [
        ("request_id", "Request ID"),
        ("occurred_at", "发生时间范围"),
        ("affected_data", "当前登录用户ID"),
        ("screenshot_notes", "截图说明"),
        ("regression_curl", "用例回归 Curl"),
        ("extra_context", "补充信息"),
    ]
    for key, title in optional_fields:
        value = record.get(key)
        if value:
            lines.extend(["", f"## {title}", value])
    attachments = record.get("screenshot_attachments") or []
    if attachments:
        lines.extend(["", "## 问题截图"])
        for attachment in attachments:
            name = attachment.get("name") or Path(str(attachment.get("path", ""))).name
            path_value = attachment.get("path") or ""
            lines.append(f"- {name}: `{path_value}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _save_bug_screenshots(body: BugPipelineCreateRequest, artifact_dir: Path, repo_path: Path) -> list[dict]:
    attachments = []
    screenshots_dir = artifact_dir / "screenshots"
    for index, image in enumerate(body.screenshot_images or [], start=1):
        suffix = _image_suffix(image.mime_type)
        original_name = Path(image.name or f"screenshot-{index}{suffix}").name
        safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(original_name).stem).strip(".-") or "screenshot"
        filename = f"{index:02d}-{safe_stem}{suffix}"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        target = screenshots_dir / filename
        data = base64.b64decode(image.data)
        target.write_bytes(data)
        attachments.append(
            {
                "name": original_name,
                "mime_type": image.mime_type,
                "size": image.size or len(data),
                "path": str(target.relative_to(repo_path)),
            }
        )
    return attachments


def _image_suffix(mime_type: str) -> str:
    return {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }.get(mime_type, ".img")


def _bug_pipeline_step_prompt(record: dict, step: str, note: str | None = None) -> str:
    artifact_dir = record["artifact_dir"]
    repo_context_lines = []
    for context in record.get("repo_contexts") or []:
        correlation = ""
        if context.get("correlation_id_name") or context.get("correlation_id_value"):
            correlation = f", {context.get('correlation_id_name') or '关联 ID'}={context.get('correlation_id_value') or '未提供'}"
        local_path = context.get("local_path") or "未记录"
        repo_context_lines.append(
            f"- {context.get('repo_name')} [{context.get('role')}]: branch={context.get('branch')}, path={local_path}{correlation}"
        )
    common = (
        f"你正在执行 fast-harness 测试环境 bug dev-fix 流水线。\n"
        f"Pipeline: {record['pipeline_id']}\n"
        f"主修复仓库: {record['repo_name']}\n"
        f"目标修复分支: {record['target_branch']}\n"
        f"当前修复分支: {record['target_branch']}\n"
        f"测试环境 namespace: {record['namespace']}\n"
        f"产物目录: {artifact_dir}\n"
        f"Bug 报告: {artifact_dir}/bug_report.md\n"
        "仓库上下文:\n"
        + ("\n".join(repo_context_lines) if repo_context_lines else "- 未提供关联仓库\n")
        + "\n约束: 只有 role=fix 的主仓库允许代码修改；role=observe 的关联仓库只用于查看 dev/观测分支代码、日志关联和调用链分析，禁止修改。\n"
    )
    if record.get("request_id"):
        common += f"request_id: {record['request_id']}\n"
    if record.get("screenshot_attachments"):
        paths = "\n".join(f"- {item.get('path')}" for item in record["screenshot_attachments"])
        common += f"问题截图附件:\n{paths}\n"
    if note:
        common += f"\n人工补充说明:\n{note}\n"

    prompts = {
        "root_cause": (
            "请执行根因分析。结合各仓库配置的关联 ID（例如 request_id/task_id）、namespace 的测试环境日志、dev 环境观测信息、"
            "主修复仓库 feature 分支代码以及关联仓库 dev/观测分支代码定位跨服务调用链根因。"
            "必要时只读查询数据库获取真实数据快照。禁止修改代码。"
            f"输出写入 {artifact_dir}/diagnosis.md，结尾给出 VERDICT: PASS 或 VERDICT: FAIL。"
        ),
        "fix_plan": (
            "请制定修复计划。先读取主修复仓库和关联仓库可用的 .wiki/ 上下文；如果 .wiki 不存在，请明确标注缺少 codewiki 并基于代码上下文制定计划。"
            f"输出写入 {artifact_dir}/fix_plan.md，内容包含跨仓库调用链判断、根因摘要、主仓库修复范围、关联仓库影响、风险、测试策略。禁止修改代码。"
        ),
        "code_generation": (
            "审批已通过。请基于修复计划执行最小化代码修复，只修改当前 bug 必要文件。"
            f"完成后写入 {artifact_dir}/changed_files.txt 和 {artifact_dir}/implementation_notes.md，输出 VERDICT。"
        ),
        "code_review": (
            "请只调用 code-reviewer-agent 执行常规代码审查，不执行安全审查。"
            f"审查 bug_report、diagnosis、fix_plan 和本次 diff，结果写入 {artifact_dir}/review_feedback.md。"
            "若有 Critical，输出 VERDICT: FAIL；否则输出 VERDICT: PASS。"
        ),
        "unit_test": (
            "请基于本次变更接口生成并运行接口级单元测试。测试数据必须优先从 dev/本地真实数据库只读查询获得，禁止凭空编造 ID。"
            f"测试代码和结果写入 {artifact_dir}/unit_test_results.md，输出 VERDICT。"
        ),
        "regression": (
            "请根据 bug_report 中测试提供的 curl 串联命令执行用例回归；如果未提供 curl，请输出需要测试补充的 curl 清单并标记阻塞。"
            f"结果写入 {artifact_dir}/regression_results.md，输出 VERDICT。"
        ),
    }
    return common + "\n" + prompts[step]


async def _finalize_bug_pipeline_step(pipeline_id: str, step: str, task: asyncio.Task | None) -> None:
    if task:
        try:
            await task
        except asyncio.CancelledError:
            current = bug_pipeline_store.require(pipeline_id)
            if current.get("status") == "terminated" or current.get("steps", {}).get(step, {}).get("status") == "skipped":
                return
            bug_pipeline_store.set_step(pipeline_id, step, "failed", "阶段已取消")
            return
    try:
        current = bug_pipeline_store.require(pipeline_id)
        if current.get("status") == "terminated" or current.get("steps", {}).get(step, {}).get("status") == "skipped":
            return
        if step == "fix_plan":
            bug_pipeline_store.update(pipeline_id, {"approval_status": "waiting"})
            bug_pipeline_store.set_step(pipeline_id, step, "waiting_approval", "修复计划已生成，等待研发审批")
            await _send_plan_approval_webhook(bug_pipeline_store.require(pipeline_id))
        else:
            bug_pipeline_store.set_step(pipeline_id, step, "passed", "阶段执行完成，请查看输出详情")
            next_step = _next_auto_step(step)
            if next_step:
                await _start_bug_pipeline_step(pipeline_id, next_step)
    except Exception as exc:
        logger.warning("Failed to finalize bug pipeline %s step %s: %s", pipeline_id, step, exc)


def _next_auto_step(step: str) -> str | None:
    if step == "root_cause":
        return "fix_plan"
    if step == "code_generation":
        return "code_review"
    if step == "code_review":
        return "unit_test"
    if step == "unit_test":
        return "regression"
    return None


async def _send_plan_approval_webhook(record: dict) -> None:
    if not settings.feishu_webhook_url:
        bug_pipeline_store.append_event(record["pipeline_id"], {"type": "webhook_skipped", "message": "FEISHU_WEBHOOK_URL is not configured"})
        return
    text = (
        f"Bug 修复计划待审批\n"
        f"Pipeline: {record['pipeline_id']}\n"
        f"Repo: {record['repo_name']}\n"
        f"Target: {record['target_branch']}\n"
        f"Push branch: {record['target_branch']}\n"
        f"Namespace: {record['namespace']}\n"
        f"请登录 fast-harness runtime 的 /bug-fix 页面审批。"
    )
    payload = json.dumps({"msg_type": "text", "content": {"text": text}}, ensure_ascii=False).encode("utf-8")

    def _post() -> None:
        req = urllib.request.Request(
            settings.feishu_webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            response.read()

    try:
        await asyncio.to_thread(_post)
        bug_pipeline_store.append_event(record["pipeline_id"], {"type": "webhook_sent", "message": "Feishu approval notification sent"})
    except Exception as exc:
        bug_pipeline_store.append_event(record["pipeline_id"], {"type": "webhook_failed", "message": str(exc)})


# ═══════════════════════ Sessions ═══════════════════════

@router.post("/sessions", response_model=SessionCreateResponse, status_code=201)
async def create_session(body: SessionCreateRequest, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    ws_rec = workspace_store.get(body.workspace_id)
    _ensure_owned(ws_rec, user_id, "Workspace not found")
    if not ws_rec.get("repos"):
        raise HTTPException(status_code=400, detail="Workspace has no bound repos")

    repo = _select_repo(ws_rec, body.repo_name)
    branch = body.branch or repo.get("branch")
    if not branch:
        raise HTTPException(status_code=400, detail="Branch is required")

    sid = uuid.uuid4().hex[:12]
    try:
        session_repo = workspace_store.create_session_worktree(
            body.workspace_id,
            repo["name"],
            sid,
            branch,
            user_id=user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    branch = getattr(session_repo, "branch", None) or branch
    session_workspace = Path(ws_rec["cwd"]) / ".session-worktrees" / sid
    try:
        sid = session_store.create(
            workspace_dir=str(session_workspace),
            metadata={
                "user_id": user_id,
                "workspace_id": body.workspace_id,
                "repo_name": repo["name"],
                "branch": branch,
                "session_repo_path": str(session_repo.local_path),
            },
            session_id=sid,
            user_id=user_id,
        )
    except Exception:
        if session_repo.local_path:
            workspace_store.remove_session_worktree(session_repo.local_path)
        raise

    rec = session_store.get(sid)
    assert rec is not None, "Session just created but not found"
    return SessionCreateResponse(session_id=sid, workspace=rec["workspace"])


def _select_repo(workspace: dict, repo_name: str | None) -> dict:
    repos = workspace.get("repos", [])
    if repo_name:
        for repo in repos:
            if repo.get("name") == repo_name:
                return repo
        raise HTTPException(status_code=404, detail=f"Repo not found: {repo_name}")
    return repos[0]


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    records = [
        record
        for record in session_store.list_all()
        if _is_bound_session(record) and _record_user_id(record) == user_id
    ]
    sessions = [SessionInfo(**r) for r in records]
    return SessionListResponse(sessions=sessions)


def _is_bound_session(record: dict) -> bool:
    return bool(record.get("metadata", {}).get("workspace_id"))


@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    rec = session_store.get(session_id)
    _ensure_owned(rec, user_id, "Session not found")
    return SessionInfo(**rec)


@router.patch("/sessions/{session_id}", response_model=SessionInfo)
async def rename_session(session_id: str, body: RenameRequest, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    _ensure_owned(session_store.get(session_id), user_id, "Session not found")
    try:
        rec = session_store.rename(session_id, body.name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return SessionInfo(**rec)


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    rec = session_store.get(session_id)
    _ensure_owned(rec, user_id, "Session not found")
    return {
        "session_id": session_id,
        "messages": session_store.list_messages(session_id),
    }


@router.post("/sessions/{session_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(session_id: str, body: FeedbackRequest, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    _ensure_owned(session_store.get(session_id), user_id, "Session not found")
    path = _append_feedback(user_id, session_id, body)
    return FeedbackResponse(status="ok", path=str(path))


@router.post("/sessions/{session_id}/git/commit", response_model=GitActionResponse)
async def commit_session_changes(session_id: str, body: GitCommitRequest, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    rec = session_store.get(session_id)
    _ensure_owned(rec, user_id, "Session not found")
    if not _is_bound_session(rec):
        raise HTTPException(status_code=400, detail="Session is not bound to a workspace")
    if _is_query_active(session_id):
        raise HTTPException(status_code=409, detail="Session already has a running query")
    try:
        repo_path = resolve_session_repo_path(session_id).resolve()
        result = git_commit_all(repo_path, body.message, user_id=user_id)
        return GitActionResponse(**result.to_dict())
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/git/status", response_model=RepoStatusResponse)
async def get_session_git_status(session_id: str, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    rec = session_store.get(session_id)
    _ensure_owned(rec, user_id, "Session not found")
    if not _is_bound_session(rec):
        raise HTTPException(status_code=400, detail="Session is not bound to a workspace")
    try:
        repo_path = resolve_session_repo_path(session_id).resolve()
        result = git_status(repo_path, user_id=user_id)
        return RepoStatusResponse(
            repo=rec.get("metadata", {}).get("repo_name", ""),
            branch=result.branch,
            ahead=result.ahead,
            behind=result.behind,
            modified=result.modified,
            untracked=result.untracked,
            clean=result.clean,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/git/diff", response_model=SessionDiffResponse)
async def get_session_git_diff(session_id: str, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    rec = session_store.get(session_id)
    _ensure_owned(rec, user_id, "Session not found")
    if not _is_bound_session(rec):
        raise HTTPException(status_code=400, detail="Session is not bound to a workspace")
    try:
        repo_path = resolve_session_repo_path(session_id).resolve()
        result = git_session_diff(repo_path)
        return SessionDiffResponse(
            repo=rec.get("metadata", {}).get("repo_name", ""),
            branch=result.branch,
            base=result.base,
            files=[f.to_dict() for f in result.files],
            clean=result.clean,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/git/commit-message", response_model=GitCommitMessageResponse)
async def suggest_session_commit_message(session_id: str, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    rec = session_store.get(session_id)
    _ensure_owned(rec, user_id, "Session not found")
    if not _is_bound_session(rec):
        raise HTTPException(status_code=400, detail="Session is not bound to a workspace")
    if _is_query_active(session_id):
        raise HTTPException(status_code=409, detail="Session already has a running query")
    repo_path = resolve_session_repo_path(session_id).resolve()
    try:
        context = commit_message_context(repo_path)
        if not context:
            return GitCommitMessageResponse(message="Update code", generated=False)
        message = await generate_commit_message(repo_path, context)
        return GitCommitMessageResponse(message=message, generated=True)
    except RuntimeError as e:
        logger.warning("AI commit message generation failed for %s: %s", session_id, e)
        return GitCommitMessageResponse(message=_fallback_commit_message(rec), generated=False)


@router.post("/sessions/{session_id}/git/push", response_model=GitActionResponse)
async def push_session_changes(session_id: str, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    rec = session_store.get(session_id)
    _ensure_owned(rec, user_id, "Session not found")
    if not _is_bound_session(rec):
        raise HTTPException(status_code=400, detail="Session is not bound to a workspace")
    if _is_query_active(session_id):
        raise HTTPException(status_code=409, detail="Session already has a running query")
    try:
        repo_path = resolve_session_repo_path(session_id).resolve()
        branch = rec.get("metadata", {}).get("branch")
        result = git_push(repo_path, branch=branch, user_id=user_id)
        return GitActionResponse(**result.to_dict())
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


def _fallback_commit_message(session: dict) -> str:
    repo = session.get("metadata", {}).get("repo_name") or "code"
    return f"Update {repo}"


def _fallback_bug_commit_message(record: dict) -> str:
    repo = record.get("repo_name") or record.get("repo_key") or "code"
    description = _branch_slug(record.get("problem_description") or "bugfix").replace("-", " ")
    return f"Fix {repo} bug: {description}"


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    rec = session_store.get(session_id)
    _ensure_owned(rec, user_id, "Session not found")
    session_repo_path = rec.get("metadata", {}).get("session_repo_path")
    if session_repo_path:
        workspace_store.remove_session_worktree(session_repo_path)
    session_store.delete(session_id)
    return {"status": "deleted", "session_id": session_id}


# ═══════════════════════ Query (SSE streaming) ═══════════════════════

class ActiveQuery:
    def __init__(self) -> None:
        self.events: list[tuple[int, dict]] = []
        self.subscribers: set[asyncio.Queue] = set()
        self.task: asyncio.Task | None = None


_active_queries: dict[str, ActiveQuery] = {}


def _is_query_active(session_id: str) -> bool:
    query = _active_queries.get(session_id)
    return bool(query and query.task and not query.task.done())


def _history_last_index(session_id: str) -> int:
    return len(session_store.list_messages(session_id)) - 1


async def _publish_query_event(active: ActiveQuery, index: int, message: dict) -> None:
    active.events.append((index, message))
    for queue in list(active.subscribers):
        await queue.put((index, message))


async def _run_query_background(
    session_id: str,
    body: QueryRequest,
    active: ActiveQuery,
) -> None:
    try:
        for msg in [{"type": "status", "status": "running"}]:
            await _publish_query_event(active, _history_last_index(session_id), msg)

        async for msg in run_query_stream(
            session_id=session_id,
            prompt=body.prompt,
            images=[image.model_dump() for image in body.images],
            allowed_tools=body.allowed_tools,
            max_turns=body.max_turns,
            max_budget_usd=body.max_budget_usd,
            permission_mode=body.permission_mode,
        ):
            session_store.append_message(session_id, msg)
            await _publish_query_event(active, _history_last_index(session_id), msg)
    except asyncio.CancelledError:
        msg = {"type": "cancelled", "message": "Request cancelled"}
        session_store.append_message(session_id, msg)
        await _publish_query_event(active, _history_last_index(session_id), msg)
        raise
    finally:
        done = {"type": "stream_done"}
        await _publish_query_event(active, _history_last_index(session_id), done)
        for queue in list(active.subscribers):
            await queue.put(None)
        _active_queries.pop(session_id, None)


def _ensure_query_started(session_id: str, body: QueryRequest) -> ActiveQuery:
    active = _active_queries.get(session_id)
    if _is_query_active(session_id) and active:
        raise HTTPException(status_code=409, detail="Session already has a running query")

    user_message = {"type": "user", "prompt": body.prompt}
    if body.images:
        user_message["images"] = [
            {
                "name": image.name,
                "mime_type": image.mime_type,
                "size": image.size,
            }
            for image in body.images
        ]
    session_store.append_message(session_id, user_message)
    active = ActiveQuery()
    active.task = asyncio.create_task(_run_query_background(session_id, body, active))
    _active_queries[session_id] = active
    return active


async def _query_event_stream(session_id: str, since: int = -1):
    active = _active_queries.get(session_id)
    if not active:
        return

    queue: asyncio.Queue = asyncio.Queue()
    active.subscribers.add(queue)
    try:
        for index, msg in active.events:
            if index > since:
                yield {"data": json.dumps(msg, ensure_ascii=False)}
        while True:
            item = await queue.get()
            if item is None:
                break
            index, msg = item
            if index > since:
                yield {"data": json.dumps(msg, ensure_ascii=False)}
    finally:
        active.subscribers.discard(queue)


@router.post("/sessions/{session_id}/query")
async def query_session(session_id: str, body: QueryRequest, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    rec = session_store.get(session_id)
    _ensure_owned(rec, user_id, "Session not found")
    if not _is_bound_session(rec):
        raise HTTPException(status_code=400, detail="Session is not bound to a workspace")
    _checkout_session_branch(rec)
    _ensure_query_started(session_id, body)
    return EventSourceResponse(_query_event_stream(session_id, since=_history_last_index(session_id)))


@router.get("/sessions/{session_id}/stream")
async def stream_session(session_id: str, since: int = -1, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    _ensure_owned(session_store.get(session_id), user_id, "Session not found")
    return EventSourceResponse(_query_event_stream(session_id, since=since))


@router.post("/sessions/{session_id}/query/cancel")
async def cancel_query(session_id: str, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    _ensure_owned(session_store.get(session_id), user_id, "Session not found")
    active = _active_queries.get(session_id)
    if not active or not active.task or active.task.done():
        return {"status": "idle"}
    active.task.cancel()
    return {"status": "cancelled"}


@router.post("/sessions/{session_id}/answer", response_model=AnswerResponse)
async def answer_question(session_id: str, body: AnswerRequest, x_user_id: UserHeader = None):
    """Accept answers to an AskUserQuestion and feed them back to the running SDK session."""
    user_id = _current_user_id(x_user_id)
    _ensure_owned(session_store.get(session_id), user_id, "Session not found")
    try:
        await provide_answers(session_id, [entry.model_dump() for entry in body.answers])
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return AnswerResponse(status="ok", answered=len(body.answers))


def _checkout_session_branch(session: dict) -> None:
    metadata = session.get("metadata", {})
    workspace_id = metadata.get("workspace_id")
    repo_name = metadata.get("repo_name")
    branch = metadata.get("branch")
    if not workspace_id or not repo_name or not branch:
        raise HTTPException(status_code=400, detail="Session is missing workspace branch metadata")
    session_repo_path = metadata.get("session_repo_path")
    if session_repo_path:
        try:
            git_checkout(Path(session_repo_path), branch, user_id=metadata.get("user_id"))
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        return
    try:
        workspace_store.checkout_branch(workspace_id, repo_name, branch)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════ Session files ═══════════════════════

def _resolve_workspace(session_id: str, user_id: str) -> Path:
    _ensure_owned(session_store.get(session_id), user_id, "Session not found")
    try:
        return resolve_session_repo_path(session_id).resolve()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sessions/{session_id}/files")
async def list_session_files(session_id: str, x_user_id: UserHeader = None):
    ws = _resolve_workspace(session_id, _current_user_id(x_user_id))
    files = []
    for p in ws.rglob("*"):
        if p.is_file() and ".git/" not in str(p):
            files.append(str(p.relative_to(ws)))
    return {"workspace": str(ws), "files": sorted(files)}


@router.get("/sessions/{session_id}/files/{file_path:path}")
async def get_session_file(session_id: str, file_path: str, x_user_id: UserHeader = None):
    ws = _resolve_workspace(session_id, _current_user_id(x_user_id))
    target = (ws / file_path).resolve()
    if not str(target).startswith(str(ws)):
        raise HTTPException(status_code=403, detail="Path traversal denied")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return JSONResponse({"path": file_path, "content": target.read_text()})


# ═══════════════════════ Workspaces ═══════════════════════

@router.post("/workspaces", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(body: WorkspaceCreateRequest, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    legacy_repo = body.repos[0] if body.repos else None
    repositories = _workspace_repositories_from_request(body, legacy_repo)
    try:
        rec = workspace_store.create(
            body.name,
            repositories=repositories,
            user_id=user_id,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return WorkspaceResponse(**rec)


def _workspace_repositories_from_request(body: WorkspaceCreateRequest, legacy_repo=None) -> list[dict]:
    if body.repo_keys:
        branches = body.repo_branches or {}
        return [
            _repo_spec_from_config(repo_key, branches.get(repo_key))
            for repo_key in body.repo_keys
        ]

    if legacy_repo or body.repo_url:
        return [{
            "url": body.repo_url or legacy_repo.url,
            "name": body.repo_name or (legacy_repo.name if legacy_repo else None),
            "branch": body.branch or (legacy_repo.branch if legacy_repo else None),
        }]

    enabled = settings.enabled_repositories
    if len(enabled) == 1:
        repo = enabled[0]
        return [_repo_spec_from_config(repo["key"], body.branch)]

    raise HTTPException(status_code=400, detail="Select at least one registered repository")


def _repo_spec_from_config(repo_key: str, branch: str | None = None) -> dict:
    try:
        repo = settings.get_repository(repo_key)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "key": repo["key"],
        "name": repo["name"],
        "url": repo["url"],
        "branch": branch or repo["default_branch"],
    }


@router.get("/workspaces", response_model=WorkspaceListResponse)
async def list_workspaces(x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    records = [
        record
        for record in workspace_store.list_all()
        if _record_user_id(record) == user_id
    ]
    return WorkspaceListResponse(workspaces=[WorkspaceResponse(**r) for r in records])


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(workspace_id: str, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    rec = workspace_store.get(workspace_id)
    _ensure_owned(rec, user_id, "Workspace not found")
    return WorkspaceResponse(**rec)


@router.patch("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def rename_workspace(workspace_id: str, body: RenameRequest, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    _ensure_owned(workspace_store.get(workspace_id), user_id, "Workspace not found")
    try:
        rec = workspace_store.rename(workspace_id, body.name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return WorkspaceResponse(**rec)


@router.delete("/workspaces/{workspace_id}")
async def delete_workspace(workspace_id: str, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    _ensure_owned(workspace_store.get(workspace_id), user_id, "Workspace not found")
    for session in session_store.list_all():
        if session.get("metadata", {}).get("workspace_id") == workspace_id and _record_user_id(session) == user_id:
            session_repo_path = session.get("metadata", {}).get("session_repo_path")
            if session_repo_path:
                workspace_store.remove_session_worktree(session_repo_path)
            session_store.delete(session["session_id"])
    workspace_store.delete(workspace_id)
    return {"status": "deleted", "workspace_id": workspace_id}


@router.get("/default-repo/branches")
async def default_repo_branches(x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    repos = settings.enabled_repositories
    if not repos:
        return {"branches": []}
    branches = remote_branches(repos[0]["url"], user_id=user_id)
    return {"branches": branches or [repos[0]["default_branch"]]}


@router.post("/workspaces/{workspace_id}/repos", response_model=WorkspaceResponse)
async def add_workspace_repo(workspace_id: str, body: WorkspaceRepoAddRequest, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    _ensure_owned(workspace_store.get(workspace_id), user_id, "Workspace not found")
    repo = _repo_spec_from_config(body.repo_key, body.branch)
    try:
        workspace_store.add_repo(
            workspace_id,
            repo["url"],
            name=repo["name"],
            branch=repo["branch"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    rec = workspace_store.get(workspace_id)
    assert rec is not None
    return WorkspaceResponse(**rec)


@router.post("/workspaces/{workspace_id}/pull")
async def pull_workspace(workspace_id: str, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    _ensure_owned(workspace_store.get(workspace_id), user_id, "Workspace not found")
    try:
        results = workspace_store.pull_all(workspace_id)
        return {"repos": results}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/workspaces/{workspace_id}/repos/{repo_name}/status", response_model=RepoStatusResponse)
async def repo_status(workspace_id: str, repo_name: str, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    _ensure_owned(workspace_store.get(workspace_id), user_id, "Workspace not found")
    try:
        s = workspace_store.repo_status(workspace_id, repo_name)
        return RepoStatusResponse(**s)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ═══════════════════════ Branches ═══════════════════════

@router.get("/workspaces/{workspace_id}/repos/{repo_name}/branches")
async def list_branches(workspace_id: str, repo_name: str, x_user_id: UserHeader = None):
    user_id = _current_user_id(x_user_id)
    _ensure_owned(workspace_store.get(workspace_id), user_id, "Workspace not found")
    try:
        branches = workspace_store.list_branches(workspace_id, repo_name)
        return {"branches": branches}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/workspaces/{workspace_id}/repos/{repo_name}/checkout")
async def checkout_branch(
    workspace_id: str,
    repo_name: str,
    branch: str = "main",
    x_user_id: UserHeader = None,
):
    user_id = _current_user_id(x_user_id)
    _ensure_owned(workspace_store.get(workspace_id), user_id, "Workspace not found")
    try:
        result = workspace_store.checkout_branch(workspace_id, repo_name, branch)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
