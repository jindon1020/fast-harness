"""
REST API routes for the fast-harness runtime service.
"""

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
    create_local_branch as git_create_local_branch,
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
    repo = _repo_spec_from_config(body.repo_key, body.target_branch)
    target_branch = _normalize_feature_branch(body.target_branch)
    git_user_id = body.reviewer_id if settings.is_reporter(user_id) else user_id
    _ensure_remote_feature_branch(repo["url"], target_branch, git_user_id)

    pipeline_id = f"bug-{uuid.uuid4().hex[:10]}"
    bugfix_branch = f"bugfix/{pipeline_id}-{_branch_slug(body.problem_description)}"
    workspace_rec = workspace_store.create(
        f"BugFix {pipeline_id}",
        repositories=[{**repo, "branch": target_branch}],
        user_id=user_id,
        git_user_id=git_user_id,
    )
    sid = uuid.uuid4().hex[:12]
    try:
        session_repo = workspace_store.create_session_worktree(
            workspace_rec["workspace_id"],
            repo["name"],
            sid,
            target_branch,
            user_id=user_id,
            git_user_id=git_user_id,
        )
        bugfix_branch = git_create_local_branch(Path(session_repo.local_path), bugfix_branch)
        session_workspace = Path(workspace_rec["cwd"]) / ".session-worktrees" / sid
        session_store.create(
            workspace_dir=str(session_workspace),
            metadata={
                "user_id": user_id,
                "workspace_id": workspace_rec["workspace_id"],
                "repo_name": repo["name"],
                "branch": bugfix_branch,
                "target_branch": target_branch,
                "bug_pipeline_id": pipeline_id,
                "session_repo_path": str(session_repo.local_path),
            },
            session_id=sid,
            user_id=user_id,
        )
    except Exception:
        local_path = getattr(locals().get("session_repo", None), "local_path", None)
        if local_path:
            workspace_store.remove_session_worktree(local_path)
        workspace_store.delete(workspace_rec["workspace_id"])
        raise

    artifact_dir = Path(session_repo.local_path) / ".ai" / "dev-fix" / pipeline_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    record = bug_pipeline_store.create(
        {
            "pipeline_id": pipeline_id,
            "user_id": user_id,
            "reviewer_id": body.reviewer_id,
            "repo_key": body.repo_key,
            "repo_name": repo["name"],
            "workspace_id": workspace_rec["workspace_id"],
            "session_id": sid,
            "target_branch": target_branch,
            "bugfix_branch": bugfix_branch,
            "namespace": body.namespace.strip(),
            "request_id": _clean_optional(body.request_id),
            "affected_api": body.affected_api.strip(),
            "problem_description": body.problem_description.strip(),
            "expected_result": body.expected_result.strip(),
            "actual_result": body.actual_result.strip(),
            "screenshot_notes": _clean_optional(body.screenshot_notes),
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
        {"type": "created", "message": f"Created {bugfix_branch} from {target_branch}"},
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


def _pipeline_session(record: dict) -> dict:
    session = session_store.get(record["session_id"])
    if not session:
        raise HTTPException(status_code=404, detail="Pipeline session not found")
    return session


def _ensure_step_can_run(record: dict, step: str) -> None:
    steps = record.get("steps") or {}
    index = PIPELINE_STEPS.index(step)
    for previous in PIPELINE_STEPS[1:index]:
        if steps.get(previous, {}).get("status") != "passed":
            raise HTTPException(status_code=409, detail=f"Previous step is not passed: {previous}")
    if step == "code_generation" and record.get("approval_status") != "approved":
        raise HTTPException(status_code=409, detail="Fix plan must be approved before code generation")
    if step == "code_generation" and int(record.get("review_retry_count") or 0) >= 3:
        raise HTTPException(status_code=409, detail="Code review retry limit reached")


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
        f"- repo: `{record['repo_name']}`",
        f"- target_branch: `{record['target_branch']}`",
        f"- bugfix_branch: `{record['bugfix_branch']}`",
        f"- reviewer_id: `{record['reviewer_id']}`",
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
    optional_fields = [
        ("request_id", "Request ID"),
        ("occurred_at", "发生时间"),
        ("affected_data", "影响用户或数据"),
        ("screenshot_notes", "截图说明"),
        ("regression_curl", "用例回归 Curl"),
        ("extra_context", "补充信息"),
    ]
    for key, title in optional_fields:
        value = record.get(key)
        if value:
            lines.extend(["", f"## {title}", value])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _bug_pipeline_step_prompt(record: dict, step: str, note: str | None = None) -> str:
    artifact_dir = record["artifact_dir"]
    common = (
        f"你正在执行 fast-harness 测试环境 bug dev-fix 流水线。\n"
        f"Pipeline: {record['pipeline_id']}\n"
        f"目标修复分支: {record['target_branch']}\n"
        f"当前临时分支: {record['bugfix_branch']}\n"
        f"测试环境 namespace: {record['namespace']}\n"
        f"产物目录: {artifact_dir}\n"
        f"Bug 报告: {artifact_dir}/bug_report.md\n"
    )
    if record.get("request_id"):
        common += f"request_id: {record['request_id']}\n"
    if note:
        common += f"\n人工补充说明:\n{note}\n"

    prompts = {
        "root_cause": (
            "请执行根因分析。结合 request_id/namespace 的测试环境日志、dev 环境观测信息和当前 feature 分支代码定位可能根因。"
            "必要时只读查询数据库获取真实数据快照。禁止修改代码。"
            f"输出写入 {artifact_dir}/diagnosis.md，结尾给出 VERDICT: PASS 或 VERDICT: FAIL。"
        ),
        "fix_plan": (
            "请制定修复计划。先读取 .wiki/ 相关上下文；如果 .wiki 不存在，请明确标注缺少 codewiki 并基于代码上下文制定计划。"
            f"输出写入 {artifact_dir}/fix_plan.md，内容包含根因摘要、修复范围、风险、测试策略。禁止修改代码。"
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
            bug_pipeline_store.set_step(pipeline_id, step, "failed", "阶段已取消")
            return
    try:
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
        f"Bugfix: {record['bugfix_branch']}\n"
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
