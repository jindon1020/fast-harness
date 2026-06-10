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


class BugPipelineCreateRequest(BaseModel):
    repo_key: str = Field(..., min_length=1)
    target_branch: str = Field(..., min_length=1, description="Remote feature branch to fix from")
    namespace: str = Field(..., min_length=1)
    affected_api: str = Field(..., min_length=1, max_length=2000)
    problem_description: str = Field(..., min_length=1, max_length=10000)
    expected_result: str = Field(..., min_length=1, max_length=5000)
    actual_result: str = Field(..., min_length=1, max_length=5000)
    reviewer_id: str = Field(..., min_length=1)
    request_id: str | None = Field(default=None, max_length=500)
    screenshot_notes: str | None = Field(default=None, max_length=2000)
    occurred_at: str | None = Field(default=None, max_length=500)
    affected_data: str | None = Field(default=None, max_length=5000)
    regression_curl: str | None = Field(default=None, max_length=20000)
    extra_context: str | None = Field(default=None, max_length=10000)


class BugPipelineStepRunRequest(BaseModel):
    note: str | None = Field(default=None, max_length=5000)


class BugPipelineApprovalRequest(BaseModel):
    approved: bool
    comment: str | None = Field(default=None, max_length=5000)


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


class BugPipelineStepInfo(BaseModel):
    id: str
    title: str
    status: str
    attempts: int = 0
    started_at: str | None = None
    completed_at: str | None = None
    summary: str = ""


class BugPipelineResponse(BaseModel):
    pipeline_id: str
    status: str
    approval_status: str
    user_id: str
    reviewer_id: str
    repo_key: str
    repo_name: str
    workspace_id: str
    session_id: str
    target_branch: str
    bugfix_branch: str
    namespace: str
    request_id: str | None = None
    affected_api: str
    problem_description: str
    expected_result: str
    actual_result: str
    artifact_dir: str
    steps: dict[str, BugPipelineStepInfo]
    events: list[dict] = Field(default_factory=list)
    created_at: str
    updated_at: str


class BugPipelineListResponse(BaseModel):
    pipelines: list[BugPipelineResponse]


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


class FileDiffSchema(BaseModel):
    path: str
    change_type: str
    additions: int = 0
    deletions: int = 0
    diff: str = ""
    old_path: str = ""
    truncated: bool = False


class SessionDiffResponse(BaseModel):
    repo: str = ""
    branch: str = ""
    base: str = "HEAD"
    files: list[FileDiffSchema] = Field(default_factory=list)
    clean: bool = True


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
