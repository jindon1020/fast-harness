from __future__ import annotations

from pydantic import BaseModel, Field


# ── Requests ──

class QueryRequest(BaseModel):
    prompt: str = Field(..., description="User prompt / task description")
    allowed_tools: list[str] | None = Field(default=None)
    max_turns: int | None = Field(default=None, ge=1, le=100)
    max_budget_usd: float | None = Field(default=None, ge=0.01)
    permission_mode: str = Field(default="acceptEdits")


class SessionCreateRequest(BaseModel):
    workspace_id: str = Field(..., description="Workspace this session belongs to")
    repo_name: str | None = Field(default=None, description="Repo to checkout before the session starts")
    branch: str | None = Field(default=None, description="Branch to checkout for this session")


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(..., description="Human-readable workspace name")
    repo_url: str | None = Field(default=None, description="Git URL; defaults to the configured creation-tool repo")
    repo_name: str | None = Field(default=None)
    branch: str | None = Field(default=None)
    repos: list[RepoInput] | None = Field(default=None, description="Legacy repo payload; first entry is used if present")


class RepoInput(BaseModel):
    url: str = Field(..., description="Git URL (HTTPS or SSH)")
    name: str | None = Field(default=None)
    branch: str | None = Field(default=None)


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
