from __future__ import annotations

import base64
import binascii

from pydantic import BaseModel, Field, field_validator


ALLOWED_IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
MAX_QUERY_IMAGES = 5
MAX_QUERY_IMAGE_BYTES = 10 * 1024 * 1024


# ── Requests ──

class QueryImageAttachment(BaseModel):
    name: str = Field(default="image", min_length=1, max_length=255)
    mime_type: str = Field(..., description="Image MIME type")
    data: str = Field(..., description="Base64 encoded image bytes")
    size: int | None = Field(default=None, ge=1, le=MAX_QUERY_IMAGE_BYTES)

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, value: str) -> str:
        if value not in ALLOWED_IMAGE_MIME_TYPES:
            raise ValueError(f"Unsupported image type: {value}")
        return value

    @field_validator("data")
    @classmethod
    def validate_base64_data(cls, value: str) -> str:
        data = value.split(",", 1)[1] if value.startswith("data:") and "," in value else value
        try:
            decoded = base64.b64decode(data, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("Image data must be valid base64") from exc
        if len(decoded) > MAX_QUERY_IMAGE_BYTES:
            raise ValueError("Image exceeds the 10MB limit")
        return data


class QueryRequest(BaseModel):
    prompt: str = Field(..., description="User prompt / task description")
    images: list[QueryImageAttachment] = Field(default_factory=list, max_length=MAX_QUERY_IMAGES)
    allowed_tools: list[str] | None = Field(default=None)
    max_turns: int | None = Field(default=None, ge=1, le=100)
    max_budget_usd: float | None = Field(default=None, ge=0.01)
    permission_mode: str = Field(default="acceptEdits")


class RenameRequest(BaseModel):
    name: str = Field(..., min_length=1, description="New display name")


class LoginRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class FeedbackRequest(BaseModel):
    feedback: str = Field(..., min_length=1, max_length=5000)
    message_excerpt: str | None = Field(default=None, max_length=2000)


class GitCommitRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)


class SessionCreateRequest(BaseModel):
    workspace_id: str = Field(..., description="Workspace this session belongs to")
    repo_name: str | None = Field(default=None, description="Repo to checkout before the session starts")
    branch: str | None = Field(default=None, description="Branch to checkout for this session")


class RepoInput(BaseModel):
    url: str = Field(..., description="Git URL (HTTPS or SSH)")
    name: str | None = Field(default=None)
    branch: str | None = Field(default=None)


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(..., description="Human-readable workspace name")
    repo_keys: list[str] | None = Field(default=None, description="Registered repository keys to enable")
    repo_branches: dict[str, str] | None = Field(default=None, description="Branch by registered repository key")
    repo_url: str | None = Field(default=None, description="Git URL; defaults to the configured creation-tool repo")
    repo_name: str | None = Field(default=None)
    branch: str | None = Field(default=None)
    repos: list[RepoInput] | None = Field(default=None, description="Legacy repo payload; first entry is used if present")


class WorkspaceRepoAddRequest(BaseModel):
    repo_key: str = Field(..., description="Registered repository key to add")
    branch: str | None = Field(default=None)


class UserInfo(BaseModel):
    id: str
    name: str
    role: str = "member"
    enabled: bool


class UserListResponse(BaseModel):
    users: list[UserInfo]
    default_user_id: str


class CurrentUserResponse(BaseModel):
    user: UserInfo


class LoginResponse(BaseModel):
    status: str
    user: UserInfo


class UsageCommandStat(BaseModel):
    command: str
    count: int


class UsageUserStat(BaseModel):
    user_id: str
    name: str
    workspace_count: int
    session_count: int
    conversation_count: int
    result_count: int
    command_count: int
    feedback_count: int
    last_active: str | None = None
    commands: list[UsageCommandStat] = Field(default_factory=list)


class UsageStatsResponse(BaseModel):
    users: list[UsageUserStat]
    totals: dict[str, int]


# ── Responses ──

class SessionCreateResponse(BaseModel):
    session_id: str
    workspace: str


class SessionInfo(BaseModel):
    session_id: str
    name: str | None = Field(default=None)
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
    user_id: str | None = Field(default=None)


class WorkspaceListResponse(BaseModel):
    workspaces: list[WorkspaceResponse]


class RepositoryConfigInfo(BaseModel):
    key: str
    name: str
    url: str
    default_branch: str
    enabled: bool


class RepositoryListResponse(BaseModel):
    repositories: list[RepositoryConfigInfo]


class RepoStatusResponse(BaseModel):
    repo: str
    branch: str
    ahead: int
    behind: int
    modified: list[str]
    untracked: list[str]
    clean: bool


class GitActionResponse(BaseModel):
    status: str
    branch: str
    stdout: str = ""
    stderr: str = ""


class GitCommitMessageResponse(BaseModel):
    message: str
    generated: bool = True


class CapabilityResponse(BaseModel):
    commands: list[dict]
    agents: dict[str, dict]
    skills: list[dict]


class AnswerEntry(BaseModel):
    question: str
    answer: str | list[str]
    tool_use_id: str


class AnswerRequest(BaseModel):
    answers: list[AnswerEntry] = Field(..., min_length=1)


class AnswerResponse(BaseModel):
    status: str
    answered: int


class FeedbackResponse(BaseModel):
    status: str
    path: str


class AnswerEntry(BaseModel):
    question: str
    answer: str
    tool_use_id: str


class AnswerRequest(BaseModel):
    answers: list[AnswerEntry] = Field(..., min_length=1)


class AnswerResponse(BaseModel):
    status: str
    answered: int


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    harness_loaded: bool
