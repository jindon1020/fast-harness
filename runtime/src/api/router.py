"""
REST API routes for the fast-harness runtime service.
"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse
from starlette.responses import JSONResponse

from src.api.schemas import (
    QueryRequest,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionInfo,
    SessionListResponse,
    WorkspaceCreateRequest,
    WorkspaceResponse,
    WorkspaceListResponse,
    RepoAddRequest,
    RepoStatusResponse,
    CapabilityResponse,
    HealthResponse,
)
from src.config import settings
from src.core.agent import run_query_stream
from src.core.sandbox import destroy_workspace
from src.core.session import session_store
from src.core.workspace import workspace_store
from src.harness.registry import get_capabilities

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


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


# ═══════════════════════ Sessions ═══════════════════════

@router.post("/sessions", response_model=SessionCreateResponse, status_code=201)
async def create_session(body: SessionCreateRequest = SessionCreateRequest()):
    workspace_dir = None
    if body.workspace_id:
        ws_rec = workspace_store.get(body.workspace_id)
        if not ws_rec:
            raise HTTPException(status_code=404, detail="Workspace not found")
        workspace_dir = ws_rec["cwd"]

    sid = session_store.create(workspace_dir=workspace_dir)
    if body.workspace_id:
        session_store.update_metadata(sid, {"workspace_id": body.workspace_id})

    rec = session_store.get(sid)
    assert rec is not None, "Session just created but not found"
    return SessionCreateResponse(session_id=sid, workspace=rec["workspace"])


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions():
    records = session_store.list_all()
    sessions = [SessionInfo(**r) for r in records]
    return SessionListResponse(sessions=sessions)


@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    rec = session_store.get(session_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionInfo(**rec)


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    rec = session_store.get(session_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Session not found")
    session_store.delete(session_id)
    # Don't destroy dir if session was in a workspace
    if not rec.get("metadata", {}).get("workspace_id"):
        destroy_workspace(session_id)
    return {"status": "deleted", "session_id": session_id}


# ═══════════════════════ Query (SSE streaming) ═══════════════════════

@router.post("/sessions/{session_id}/query")
async def query_session(session_id: str, body: QueryRequest):
    rec = session_store.get(session_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_stream():
        async for msg in run_query_stream(
            session_id=session_id,
            prompt=body.prompt,
            workspace_id=body.workspace_id,
            allowed_tools=body.allowed_tools,
            max_turns=body.max_turns,
            max_budget_usd=body.max_budget_usd,
            permission_mode=body.permission_mode,
        ):
            yield {"data": json.dumps(msg, ensure_ascii=False)}

    return EventSourceResponse(event_stream())


# ═══════════════════════ Session files ═══════════════════════

def _resolve_workspace(session_id: str) -> Path:
    rec = session_store.get(session_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Session not found")
    ws = Path(rec["workspace"])
    if not ws.exists():
        raise HTTPException(status_code=404, detail="Workspace directory not found")
    return ws.resolve()


@router.get("/sessions/{session_id}/files")
async def list_session_files(session_id: str):
    ws = _resolve_workspace(session_id)
    files = []
    for p in ws.rglob("*"):
        if p.is_file() and ".git/" not in str(p):
            files.append(str(p.relative_to(ws)))
    return {"workspace": str(ws), "files": sorted(files)}


@router.get("/sessions/{session_id}/files/{file_path:path}")
async def get_session_file(session_id: str, file_path: str):
    ws = _resolve_workspace(session_id)
    target = (ws / file_path).resolve()
    if not str(target).startswith(str(ws)):
        raise HTTPException(status_code=403, detail="Path traversal denied")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return JSONResponse({"path": file_path, "content": target.read_text()})


# ═══════════════════════ Workspaces ═══════════════════════

@router.post("/workspaces", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(body: WorkspaceCreateRequest):
    repos_dicts = [r.model_dump() for r in body.repos] if body.repos else None
    rec = workspace_store.create(body.name, repos_dicts)
    return WorkspaceResponse(**rec)


@router.get("/workspaces", response_model=WorkspaceListResponse)
async def list_workspaces():
    records = workspace_store.list_all()
    return WorkspaceListResponse(workspaces=[WorkspaceResponse(**r) for r in records])


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(workspace_id: str):
    rec = workspace_store.get(workspace_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return WorkspaceResponse(**rec)


@router.delete("/workspaces/{workspace_id}")
async def delete_workspace(workspace_id: str):
    if not workspace_store.get(workspace_id):
        raise HTTPException(status_code=404, detail="Workspace not found")
    workspace_store.delete(workspace_id)
    return {"status": "deleted", "workspace_id": workspace_id}


# ═══════════════════════ Repos ═══════════════════════

@router.post("/workspaces/{workspace_id}/repos")
async def add_repo(workspace_id: str, body: RepoAddRequest):
    try:
        repo = workspace_store.add_repo(workspace_id, body.url, body.name, body.branch)
        return repo.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/workspaces/{workspace_id}/repos/{repo_name}")
async def remove_repo(workspace_id: str, repo_name: str):
    try:
        workspace_store.remove_repo(workspace_id, repo_name)
        return {"status": "deleted", "repo": repo_name}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/workspaces/{workspace_id}/pull")
async def pull_workspace(workspace_id: str):
    try:
        results = workspace_store.pull_all(workspace_id)
        return {"repos": results}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/workspaces/{workspace_id}/repos/{repo_name}/status", response_model=RepoStatusResponse)
async def repo_status(workspace_id: str, repo_name: str):
    try:
        s = workspace_store.repo_status(workspace_id, repo_name)
        return RepoStatusResponse(**s)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ═══════════════════════ Branches ═══════════════════════

@router.get("/workspaces/{workspace_id}/repos/{repo_name}/branches")
async def list_branches(workspace_id: str, repo_name: str):
    try:
        branches = workspace_store.list_branches(workspace_id, repo_name)
        return {"branches": branches}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/workspaces/{workspace_id}/repos/{repo_name}/checkout")
async def checkout_branch(workspace_id: str, repo_name: str, branch: str = "main"):
    try:
        result = workspace_store.checkout_branch(workspace_id, repo_name, branch)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════ Registered Repos ═══════════════════════

@router.get("/repos/registered")
async def registered_repos():
    repos = workspace_store.get_registered_repos()
    return {"repos": repos}
