from __future__ import annotations

from pydantic import BaseModel, Field


# ── Requests ──

class QueryRequest(BaseModel):
    prompt: str = Field(..., description="User prompt / task description")
    workspace_id: str | None = Field(default=None, description="Workspace to operate in (overrides session default)")
    allowed_tools: list[str] | None = Field(default=None)
    max_turns: int | None = Field(default=None, ge=1, le=100)
    max_budget_usd: float | None = Field(default=None, ge=0.01)
    permission_mode: str = Field(default="acceptEdits")


class SessionCreateRequest(BaseModel):
    workspace_id: str | None = Field(default=None, description="Bind session to an existing workspace")


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(..., description="Human-readable workspace name")
    repos: list[RepoInput] = Field(default_factory=list, description="Initial repos to clone")


class RepoInput(BaseModel):
    url: str = Field(..., description="Git URL (HTTPS or SSH)")
    name: str | None = Field(default=None)
    branch: str | None = Field(default=None)


class RepoAddRequest(BaseModel):
    url: str
    name: str | None = None
    branch: str | None = None


# ── Responses ──

class SessionCreateResponse(BaseModel):
    session_id: str
    workspace: str


class SessionInfo(BaseModel):
    session_id: str
    workspace: str
    created_at: str
    last_access: str
    metadata: dict = Field(default_factory=dict)


class SessionListResponse(BaseModel):
    sessions: list[SessionInfo]


class WorkspaceResponse(BaseModel):
    workspace_id: str
    name: str
    cwd: str
    repos: list[dict]
    created_at: str
    updated_at: str


class WorkspaceListResponse(BaseModel):
    workspaces: list[WorkspaceResponse]


class RepoStatusResponse(BaseModel):
    repo: str
    branch: str
    ahead: int
    behind: int
    modified: list[str]
    untracked: list[str]
    clean: bool


class CapabilityResponse(BaseModel):
    commands: list[dict]
    agents: dict[str, dict]
    skills: list[dict]


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    harness_loaded: bool
