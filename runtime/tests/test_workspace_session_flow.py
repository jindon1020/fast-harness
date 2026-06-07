import json
import asyncio

import pytest
from types import SimpleNamespace
from fastapi import HTTPException
from pydantic import ValidationError

from src.api import router
from src.api.schemas import (
    FeedbackRequest,
    GitCommitRequest,
    RenameRequest,
    SessionCreateRequest,
    WorkspaceCreateRequest,
    WorkspaceRepoAddRequest,
)
from src.core import session
from src.core import workspace
from src.core.agent import _resolve_cwd


def test_workspace_creation_defaults_to_creation_tool_repo():
    request = WorkspaceCreateRequest(
        name="repo-ws",
        repo_keys=["app"],
        repo_branches={"app": "feature/x"},
    )

    assert request.repo_keys == ["app"]
    assert request.repo_branches == {"app": "feature/x"}


@pytest.mark.asyncio
async def test_workspace_creation_uses_selected_registered_repositories(monkeypatch):
    class FakeWorkspaceStore:
        def __init__(self):
            self.created = None

        def create(self, name, repositories, user_id=None):
            self.created = (name, repositories, user_id)
            return {
                "workspace_id": "ws-1",
                "name": name,
                "cwd": "/tmp/ws-1",
                "user_id": user_id,
                "repos": [
                    {"name": repo["name"], "branch": repo["branch"]}
                    for repo in repositories
                ],
                "created_at": "now",
                "updated_at": "now",
            }

    repos = {
        "app": {
            "key": "app",
            "name": "app-service",
            "url": "https://example.com/app.git",
            "default_branch": "main",
            "enabled": True,
        },
        "api": {
            "key": "api",
            "name": "api-service",
            "url": "https://example.com/api.git",
            "default_branch": "develop",
            "enabled": True,
        },
    }

    fake_store = FakeWorkspaceStore()
    monkeypatch.setattr(router, "workspace_store", fake_store)
    monkeypatch.setattr(type(router.settings), "get_repository", lambda self, key: repos[key])

    response = await router.create_workspace(
        WorkspaceCreateRequest(
            name="repo-ws",
            repo_keys=["app", "api"],
            repo_branches={"app": "feature/x"},
        )
    )

    assert fake_store.created[2] == "zhaojindong"
    assert [repo["name"] for repo in fake_store.created[1]] == [
        "app-service",
        "api-service",
    ]
    assert [repo["branch"] for repo in fake_store.created[1]] == [
        "feature/x",
        "develop",
    ]
    assert [repo["name"] for repo in response.repos] == ["app-service", "api-service"]


@pytest.mark.asyncio
async def test_workspace_creation_returns_bad_request_for_git_errors(monkeypatch):
    class FakeWorkspaceStore:
        def create(self, name, repositories, user_id=None):
            raise RuntimeError("Worktree creation failed: fatal: invalid reference: origin/main")

    repo = {
        "key": "app",
        "name": "app-service",
        "url": "https://example.com/app.git",
        "default_branch": "main",
        "enabled": True,
    }

    monkeypatch.setattr(router, "workspace_store", FakeWorkspaceStore())
    monkeypatch.setattr(type(router.settings), "get_repository", lambda self, key: repo)

    with pytest.raises(HTTPException) as exc_info:
        await router.create_workspace(
            WorkspaceCreateRequest(name="repo-ws", repo_keys=["app"])
        )

    assert exc_info.value.status_code == 400
    assert "invalid reference" in exc_info.value.detail


@pytest.mark.asyncio
async def test_workspace_can_add_registered_repo_after_creation(monkeypatch):
    class FakeWorkspaceStore:
        def __init__(self):
            self.added = None

        def get(self, workspace_id):
            return {
                "workspace_id": workspace_id,
                "name": "repo-ws",
                "cwd": "/tmp/ws-1",
                "repos": [],
                "created_at": "now",
                "updated_at": "now",
            }

        def add_repo(self, workspace_id, url, name=None, branch=None):
            self.added = (workspace_id, url, name, branch)
            return None

    repo = {
        "key": "app",
        "name": "app-service",
        "url": "https://example.com/app.git",
        "default_branch": "main",
        "enabled": True,
    }
    fake_store = FakeWorkspaceStore()
    monkeypatch.setattr(router, "workspace_store", fake_store)
    monkeypatch.setattr(type(router.settings), "get_repository", lambda self, key: repo)

    await router.add_workspace_repo(
        "ws-1",
        WorkspaceRepoAddRequest(repo_key="app", branch="feature/x"),
    )

    assert fake_store.added == (
        "ws-1",
        "https://example.com/app.git",
        "app-service",
        "feature/x",
    )


def test_session_creation_requires_workspace():
    with pytest.raises(ValidationError):
        SessionCreateRequest()


@pytest.mark.asyncio
async def test_workspace_can_be_renamed(monkeypatch):
    class FakeWorkspaceStore:
        def __init__(self):
            self.renamed = None

        def get(self, workspace_id):
            return {
                "workspace_id": workspace_id,
                "name": "old",
                "cwd": "/tmp/ws-1",
                "repos": [],
                "created_at": "now",
                "updated_at": "now",
            }

        def rename(self, workspace_id, name):
            self.renamed = (workspace_id, name)
            return {
                "workspace_id": workspace_id,
                "name": name,
                "cwd": "/tmp/ws-1",
                "repos": [],
                "created_at": "now",
                "updated_at": "later",
            }

    fake_store = FakeWorkspaceStore()
    monkeypatch.setattr(router, "workspace_store", fake_store)

    response = await router.rename_workspace("ws-1", RenameRequest(name="新工作区"))

    assert fake_store.renamed == ("ws-1", "新工作区")
    assert response.name == "新工作区"


@pytest.mark.asyncio
async def test_session_can_be_renamed(monkeypatch):
    class FakeSessionStore:
        def __init__(self):
            self.renamed = None

        def get(self, session_id):
            return {
                "session_id": session_id,
                "workspace": "/tmp/ws-1",
                "created_at": "now",
                "last_access": "now",
                "metadata": {"workspace_id": "ws-1"},
            }

        def rename(self, session_id, name):
            self.renamed = (session_id, name)
            return {
                "session_id": session_id,
                "name": name,
                "workspace": "/tmp/ws-1",
                "created_at": "now",
                "last_access": "later",
                "metadata": {"workspace_id": "ws-1"},
            }

    fake_store = FakeSessionStore()
    monkeypatch.setattr(router, "session_store", fake_store)

    response = await router.rename_session("sess-1", RenameRequest(name="需求设计"))

    assert fake_store.renamed == ("sess-1", "需求设计")
    assert response.name == "需求设计"


@pytest.mark.asyncio
async def test_session_creation_binds_workspace_branch(monkeypatch, tmp_path):
    class FakeWorkspaceStore:
        def __init__(self):
            self.session_worktree = None

        def get(self, workspace_id):
            assert workspace_id == "ws-1"
            return {
                "workspace_id": "ws-1",
                "cwd": str(tmp_path),
                "repos": [{"name": "app", "branch": "main", "url": "https://example.com/app.git"}],
            }

        def create_session_worktree(self, workspace_id, repo_name, session_id, branch, user_id=None):
            self.session_worktree = (workspace_id, repo_name, session_id, branch, user_id)
            return SimpleNamespace(local_path=tmp_path / ".session-worktrees" / session_id / repo_name)

        def remove_session_worktree(self, repo_path):
            raise AssertionError("session worktree should not be removed on successful creation")

    class FakeSessionStore:
        def __init__(self):
            self.metadata = None
            self.workspace_dir = None
            self.session_id = None

        def create(self, *, workspace_dir, metadata, session_id=None, user_id=None):
            self.workspace_dir = workspace_dir
            self.metadata = metadata
            self.session_id = session_id
            self.user_id = user_id
            return session_id

        def get(self, session_id):
            assert session_id == self.session_id
            return {
                "session_id": session_id,
                "workspace": self.workspace_dir,
                "created_at": "now",
                "last_access": "now",
                "metadata": self.metadata,
            }

    fake_workspace_store = FakeWorkspaceStore()
    fake_session_store = FakeSessionStore()
    monkeypatch.setattr(router, "workspace_store", fake_workspace_store)
    monkeypatch.setattr(router, "session_store", fake_session_store)

    response = await router.create_session(
        SessionCreateRequest(workspace_id="ws-1", repo_name="app", branch="feature/x")
    )

    assert response.session_id == fake_session_store.session_id
    assert fake_workspace_store.session_worktree == (
        "ws-1",
        "app",
        fake_session_store.session_id,
        "feature/x",
        "zhaojindong",
    )
    assert fake_session_store.workspace_dir == str(
        tmp_path / ".session-worktrees" / fake_session_store.session_id
    )
    assert fake_session_store.metadata == {
        "user_id": "zhaojindong",
        "workspace_id": "ws-1",
        "repo_name": "app",
        "branch": "feature/x",
        "session_repo_path": str(
            tmp_path / ".session-worktrees" / fake_session_store.session_id / "app"
        ),
    }
    assert fake_session_store.user_id == "zhaojindong"


@pytest.mark.asyncio
async def test_session_creation_records_normalized_worktree_branch(monkeypatch, tmp_path):
    class FakeWorkspaceStore:
        def get(self, workspace_id):
            return {
                "workspace_id": workspace_id,
                "cwd": str(tmp_path),
                "repos": [{"name": "app", "branch": "+ feature/sp11_01", "url": "https://example.com/app.git"}],
            }

        def create_session_worktree(self, workspace_id, repo_name, session_id, branch, user_id=None):
            assert branch == "+ feature/sp11_01"
            assert user_id == "zhaojindong"
            return SimpleNamespace(
                branch="feature/sp11_01",
                local_path=tmp_path / ".session-worktrees" / session_id / repo_name,
            )

        def remove_session_worktree(self, repo_path):
            raise AssertionError("session worktree should not be removed on successful creation")

    class FakeSessionStore:
        def __init__(self):
            self.metadata = None

        def create(self, *, workspace_dir, metadata, session_id=None, user_id=None):
            self.metadata = metadata
            return session_id

        def get(self, session_id):
            return {
                "session_id": session_id,
                "workspace": str(tmp_path / ".session-worktrees" / session_id),
                "created_at": "now",
                "last_access": "now",
                "metadata": self.metadata,
            }

    fake_session_store = FakeSessionStore()
    monkeypatch.setattr(router, "workspace_store", FakeWorkspaceStore())
    monkeypatch.setattr(router, "session_store", fake_session_store)

    await router.create_session(SessionCreateRequest(workspace_id="ws-1", repo_name="app"))

    assert fake_session_store.metadata["branch"] == "feature/sp11_01"


@pytest.mark.asyncio
async def test_workspace_deletion_removes_bound_sessions(monkeypatch):
    class FakeWorkspaceStore:
        def __init__(self):
            self.deleted = []

        def get(self, workspace_id):
            return {"workspace_id": workspace_id}

        def delete(self, workspace_id):
            self.deleted.append(workspace_id)

    class FakeSessionStore:
        def __init__(self):
            self.deleted = []

        def list_all(self):
            return [
                {"session_id": "s1", "metadata": {"workspace_id": "ws-1"}},
                {"session_id": "s2", "metadata": {"workspace_id": "ws-2"}},
            ]

        def delete(self, session_id):
            self.deleted.append(session_id)

    fake_workspace_store = FakeWorkspaceStore()
    fake_session_store = FakeSessionStore()
    monkeypatch.setattr(router, "workspace_store", fake_workspace_store)
    monkeypatch.setattr(router, "session_store", fake_session_store)

    await router.delete_workspace("ws-1")

    assert fake_workspace_store.deleted == ["ws-1"]
    assert fake_session_store.deleted == ["s1"]


@pytest.mark.asyncio
async def test_workspaces_are_scoped_to_current_user(monkeypatch):
    monkeypatch.setattr(
        router.workspace_store,
        "list_all",
        lambda: [
            {
                "workspace_id": "legacy",
                "name": "legacy",
                "cwd": "/tmp/legacy",
                "repos": [],
                "created_at": "now",
                "updated_at": "now",
            },
            {
                "workspace_id": "ws-user01",
                "name": "user01",
                "cwd": "/tmp/ws-user01",
                "repos": [],
                "user_id": "user01",
                "created_at": "now",
                "updated_at": "now",
            },
        ],
    )

    default_response = await router.list_workspaces()
    user_response = await router.list_workspaces(x_user_id="user01")

    assert [workspace.workspace_id for workspace in default_response.workspaces] == ["legacy"]
    assert [workspace.workspace_id for workspace in user_response.workspaces] == ["ws-user01"]


@pytest.mark.asyncio
async def test_legacy_sessions_are_hidden_from_list(monkeypatch, tmp_path):
    monkeypatch.setattr(
        router.session_store,
        "list_all",
        lambda: [
            {
                "session_id": "legacy",
                "workspace": str(tmp_path / "legacy"),
                "created_at": "now",
                "last_access": "now",
                "metadata": {},
            },
            {
                "session_id": "bound",
                "workspace": str(tmp_path / "bound"),
                "created_at": "now",
                "last_access": "now",
                "metadata": {"workspace_id": "ws-1", "repo_name": "app", "branch": "main"},
            },
        ],
    )

    response = await router.list_sessions()
    assert [session.session_id for session in response.sessions] == ["bound"]


@pytest.mark.asyncio
async def test_legacy_sessions_belong_to_default_user(monkeypatch, tmp_path):
    monkeypatch.setattr(
        router.session_store,
        "list_all",
        lambda: [
            {
                "session_id": "legacy-default",
                "workspace": str(tmp_path / "legacy-default"),
                "created_at": "now",
                "last_access": "now",
                "metadata": {"workspace_id": "ws-1", "repo_name": "app", "branch": "main"},
            },
            {
                "session_id": "other-user",
                "workspace": str(tmp_path / "other-user"),
                "created_at": "now",
                "last_access": "now",
                "user_id": "user01",
                "metadata": {"workspace_id": "ws-2", "repo_name": "app", "branch": "main"},
            },
        ],
    )

    default_response = await router.list_sessions()
    other_response = await router.list_sessions(x_user_id="user01")

    assert [session.session_id for session in default_response.sessions] == ["legacy-default"]
    assert [session.session_id for session in other_response.sessions] == ["other-user"]


@pytest.mark.asyncio
async def test_query_rejects_legacy_unbound_session(monkeypatch, tmp_path):
    monkeypatch.setattr(
        router.session_store,
        "get",
        lambda session_id: {
            "session_id": session_id,
            "workspace": str(tmp_path),
            "created_at": "now",
            "last_access": "now",
            "metadata": {},
        },
    )

    with pytest.raises(HTTPException) as exc_info:
        await router.query_session("legacy", router.QueryRequest(prompt="hi"))

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_query_checks_out_session_branch_before_streaming(monkeypatch, tmp_path):
    class FakeWorkspaceStore:
        def __init__(self):
            self.checked_out = None

        def checkout_branch(self, workspace_id, repo_name, branch):
            self.checked_out = (workspace_id, repo_name, branch)

    async def fake_run_query_stream(**kwargs):
        yield {"type": "result", "result": "ok"}

    fake_workspace_store = FakeWorkspaceStore()
    appended_messages = []
    monkeypatch.setattr(router, "workspace_store", fake_workspace_store)
    monkeypatch.setattr(
        router.session_store,
        "get",
        lambda session_id: {
            "session_id": session_id,
            "workspace": str(tmp_path),
            "created_at": "now",
            "last_access": "now",
            "metadata": {"workspace_id": "ws-1", "repo_name": "app", "branch": "main"},
        },
    )
    monkeypatch.setattr(
        router.session_store,
        "append_message",
        lambda session_id, message: appended_messages.append(message),
    )
    monkeypatch.setattr(router, "run_query_stream", fake_run_query_stream)

    response = await router.query_session("sess-1", router.QueryRequest(prompt="hi"))
    async for _event in response.body_iterator:
        break

    assert fake_workspace_store.checked_out == ("ws-1", "app", "main")
    assert appended_messages == [
        {"type": "user", "prompt": "hi"},
        {"type": "result", "result": "ok"},
    ]


@pytest.mark.asyncio
async def test_query_passes_image_attachments_to_agent_without_storing_base64(monkeypatch, tmp_path):
    captured = {}

    class FakeWorkspaceStore:
        def checkout_branch(self, workspace_id, repo_name, branch):
            pass

    async def fake_run_query_stream(**kwargs):
        captured.update(kwargs)
        yield {"type": "result", "result": "ok"}

    appended_messages = []
    monkeypatch.setattr(router, "workspace_store", FakeWorkspaceStore())
    monkeypatch.setattr(
        router.session_store,
        "get",
        lambda session_id: {
            "session_id": session_id,
            "workspace": str(tmp_path),
            "created_at": "now",
            "last_access": "now",
            "metadata": {"workspace_id": "ws-1", "repo_name": "app", "branch": "main"},
        },
    )
    monkeypatch.setattr(
        router.session_store,
        "append_message",
        lambda session_id, message: appended_messages.append(message),
    )
    monkeypatch.setattr(router, "run_query_stream", fake_run_query_stream)

    request = router.QueryRequest(
        prompt="look",
        images=[{"name": "paste.png", "mime_type": "image/png", "data": "aGVsbG8=", "size": 5}],
    )
    response = await router.query_session("sess-1", request)
    async for _event in response.body_iterator:
        break

    assert captured["images"] == [
        {"name": "paste.png", "mime_type": "image/png", "data": "aGVsbG8=", "size": 5}
    ]
    assert appended_messages[0] == {
        "type": "user",
        "prompt": "look",
        "images": [{"name": "paste.png", "mime_type": "image/png", "size": 5}],
    }


@pytest.mark.asyncio
async def test_running_query_can_be_streamed_after_reconnect(monkeypatch, tmp_path):
    class FakeWorkspaceStore:
        def checkout_branch(self, workspace_id, repo_name, branch):
            pass

    ready = asyncio.Event()
    release = asyncio.Event()
    appended_messages = []

    async def fake_run_query_stream(**kwargs):
        ready.set()
        await release.wait()
        yield {"type": "result", "result": "ok"}

    monkeypatch.setattr(router, "workspace_store", FakeWorkspaceStore())
    monkeypatch.setattr(
        router.session_store,
        "get",
        lambda session_id: {
            "session_id": session_id,
            "workspace": str(tmp_path),
            "created_at": "now",
            "last_access": "now",
            "metadata": {"workspace_id": "ws-1", "repo_name": "app", "branch": "main"},
        },
    )
    monkeypatch.setattr(
        router.session_store,
        "append_message",
        lambda session_id, message: appended_messages.append(message),
    )
    monkeypatch.setattr(
        router.session_store,
        "list_messages",
        lambda session_id: [{"message": message} for message in appended_messages],
    )
    monkeypatch.setattr(router, "run_query_stream", fake_run_query_stream)
    router._active_queries.clear()

    await router.query_session("sess-1", router.QueryRequest(prompt="hi"))
    await asyncio.wait_for(ready.wait(), timeout=1)
    response = await router.stream_session("sess-1", since=0)
    release.set()

    events = []
    async for event in response.body_iterator:
        events.append(event)

    assert any('"result": "ok"' in event["data"] for event in events)
    assert appended_messages == [
        {"type": "user", "prompt": "hi"},
        {"type": "result", "result": "ok"},
    ]
    router._active_queries.clear()


@pytest.mark.asyncio
async def test_session_access_is_scoped_to_current_user(monkeypatch, tmp_path):
    monkeypatch.setattr(
        router.session_store,
        "get",
        lambda session_id: {
            "session_id": session_id,
            "workspace": str(tmp_path),
            "created_at": "now",
            "last_access": "now",
            "user_id": "user01",
            "metadata": {"workspace_id": "ws-1", "repo_name": "app", "branch": "main", "user_id": "user01"},
        },
    )

    with pytest.raises(HTTPException) as exc_info:
        await router.get_session("sess-1", x_user_id="user02")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_feedback_is_saved_by_user(monkeypatch, tmp_path):
    monkeypatch.setattr(router, "FEEDBACK_PATH", tmp_path / "feedback.md")
    monkeypatch.setattr(
        router.session_store,
        "get",
        lambda session_id: {
            "session_id": session_id,
            "workspace": str(tmp_path),
            "created_at": "now",
            "last_access": "now",
            "user_id": "zhaojindong",
            "metadata": {"workspace_id": "ws-1", "user_id": "zhaojindong"},
        },
    )

    response = await router.submit_feedback(
        "sess-1",
        FeedbackRequest(feedback="回复不够准确", message_excerpt="AI answer"),
    )

    content = (tmp_path / "feedback.md").read_text(encoding="utf-8")
    assert response.status == "ok"
    assert "## zhaojindong" in content
    assert "session_id: `sess-1`" in content
    assert "> 回复不够准确" in content
    assert "> AI answer" in content


@pytest.mark.asyncio
async def test_feedback_rejects_cross_user_session(monkeypatch, tmp_path):
    monkeypatch.setattr(router, "FEEDBACK_PATH", tmp_path / "feedback.md")
    monkeypatch.setattr(
        router.session_store,
        "get",
        lambda session_id: {
            "session_id": session_id,
            "workspace": str(tmp_path),
            "created_at": "now",
            "last_access": "now",
            "user_id": "user01",
            "metadata": {"workspace_id": "ws-1", "user_id": "user01"},
        },
    )

    with pytest.raises(HTTPException) as exc_info:
        await router.submit_feedback(
            "sess-1",
            FeedbackRequest(feedback="test"),
            x_user_id="zhaojindong",
        )

    assert exc_info.value.status_code == 404
    assert not (tmp_path / "feedback.md").exists()


@pytest.mark.asyncio
async def test_usage_stats_aggregates_by_user(monkeypatch, tmp_path):
    feedback_path = tmp_path / "feedback.md"
    feedback_path.write_text(
        """
# Feedback

## zhaojindong

### 2026-05-31T01:00:00+00:00

## user01

### 2026-05-31T02:00:00+00:00
### 2026-05-31T03:00:00+00:00
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(router, "FEEDBACK_PATH", feedback_path)

    class FakeWorkspaceStore:
        def list_all(self):
            return [
                {"workspace_id": "ws-1", "user_id": "zhaojindong"},
                {"workspace_id": "ws-2", "user_id": "user01"},
            ]

    class FakeSessionStore:
        def list_all(self):
            return [
                {
                    "session_id": "s1",
                    "user_id": "zhaojindong",
                    "last_access": "2026-05-31T04:00:00+00:00",
                    "metadata": {"workspace_id": "ws-1"},
                },
                {
                    "session_id": "s2",
                    "user_id": "user01",
                    "last_access": "2026-05-31T05:00:00+00:00",
                    "metadata": {"workspace_id": "ws-2"},
                },
            ]

        def list_messages(self, session_id):
            if session_id == "s1":
                return [
                    {"timestamp": "2026-05-31T04:01:00+00:00", "message": {"type": "user", "prompt": "/implement build api"}},
                    {"timestamp": "2026-05-31T04:02:00+00:00", "message": {"type": "result", "result": "ok"}},
                    {"timestamp": "2026-05-31T04:03:00+00:00", "message": {"type": "user", "prompt": "plain chat"}},
                ]
            return [
                {"timestamp": "2026-05-31T05:01:00+00:00", "message": {"type": "user", "prompt": "/fix bug"}},
                {"timestamp": "2026-05-31T05:02:00+00:00", "message": {"type": "user", "prompt": "/fix retry"}},
            ]

    monkeypatch.setattr(router, "workspace_store", FakeWorkspaceStore())
    monkeypatch.setattr(router, "session_store", FakeSessionStore())

    response = await router.usage_stats()
    by_user = {item.user_id: item for item in response.users}

    assert by_user["zhaojindong"].conversation_count == 2
    assert by_user["zhaojindong"].result_count == 1
    assert by_user["zhaojindong"].command_count == 1
    assert by_user["zhaojindong"].commands[0].command == "implement"
    assert by_user["zhaojindong"].feedback_count == 1
    assert by_user["user01"].command_count == 2
    assert by_user["user01"].commands[0].command == "fix"
    assert by_user["user01"].feedback_count == 2
    assert response.totals["conversation_count"] == 4


@pytest.mark.asyncio
async def test_query_checks_out_session_specific_repo(monkeypatch, tmp_path):
    repo_path = tmp_path / ".session-worktrees" / "sess-1" / "app"
    repo_path.mkdir(parents=True)
    checked_out = []

    async def fake_run_query_stream(**kwargs):
        yield {"type": "result", "result": "ok"}

    monkeypatch.setattr(router, "git_checkout", lambda path, branch, user_id=None: checked_out.append((path, branch, user_id)))
    monkeypatch.setattr(
        router.workspace_store,
        "checkout_branch",
        lambda workspace_id, repo_name, branch: (_ for _ in ()).throw(
            AssertionError("shared workspace repo should not be checked out")
        ),
    )
    monkeypatch.setattr(
        router.session_store,
        "get",
        lambda session_id: {
            "session_id": session_id,
            "workspace": str(repo_path.parent),
            "created_at": "now",
            "last_access": "now",
            "metadata": {
                "workspace_id": "ws-1",
                "repo_name": "app",
                "branch": "main",
                "session_repo_path": str(repo_path),
                "user_id": "zhaojindong",
            },
        },
    )
    monkeypatch.setattr(router.session_store, "append_message", lambda session_id, message: None)
    monkeypatch.setattr(router, "run_query_stream", fake_run_query_stream)

    response = await router.query_session("sess-1", router.QueryRequest(prompt="hi"))
    async for _event in response.body_iterator:
        break

    assert checked_out == [(repo_path, "main", "zhaojindong")]


@pytest.mark.asyncio
async def test_session_git_commit_uses_bound_repo_and_current_user(monkeypatch, tmp_path):
    repo_path = tmp_path / "app"
    repo_path.mkdir()
    calls = []

    monkeypatch.setattr(
        router.session_store,
        "get",
        lambda session_id: {
            "session_id": session_id,
            "workspace": str(repo_path.parent),
            "created_at": "now",
            "last_access": "now",
            "user_id": "zhaojindong",
            "metadata": {
                "workspace_id": "ws-1",
                "repo_name": "app",
                "branch": "main",
                "session_repo_path": str(repo_path),
                "user_id": "zhaojindong",
            },
        },
    )
    monkeypatch.setattr(router, "_is_query_active", lambda session_id: False)
    monkeypatch.setattr(router, "resolve_session_repo_path", lambda session_id: repo_path)

    def fake_commit(path, message, user_id=None):
        calls.append((path, message, user_id))
        return SimpleNamespace(to_dict=lambda: {"status": "committed", "branch": "main", "stdout": "ok", "stderr": ""})

    monkeypatch.setattr(router, "git_commit_all", fake_commit)

    response = await router.commit_session_changes("sess-1", GitCommitRequest(message="ship changes"))

    assert calls == [(repo_path, "ship changes", "zhaojindong")]
    assert response.status == "committed"
    assert response.branch == "main"


@pytest.mark.asyncio
async def test_session_git_commit_message_uses_ai_suggestion(monkeypatch, tmp_path):
    repo_path = tmp_path / "app"
    repo_path.mkdir()

    monkeypatch.setattr(
        router.session_store,
        "get",
        lambda session_id: {
            "session_id": session_id,
            "workspace": str(repo_path.parent),
            "created_at": "now",
            "last_access": "now",
            "user_id": "zhaojindong",
            "metadata": {
                "workspace_id": "ws-1",
                "repo_name": "app",
                "branch": "main",
                "session_repo_path": str(repo_path),
                "user_id": "zhaojindong",
            },
        },
    )
    monkeypatch.setattr(router, "_is_query_active", lambda session_id: False)
    monkeypatch.setattr(router, "resolve_session_repo_path", lambda session_id: repo_path)
    monkeypatch.setattr(router, "commit_message_context", lambda path: "## status\n M app.py")

    async def fake_generate(path, context):
        assert path == repo_path
        assert "app.py" in context
        return "Update app behavior"

    monkeypatch.setattr(router, "generate_commit_message", fake_generate)

    response = await router.suggest_session_commit_message("sess-1")

    assert response.message == "Update app behavior"
    assert response.generated is True


@pytest.mark.asyncio
async def test_session_git_commit_message_falls_back_on_ai_failure(monkeypatch, tmp_path):
    repo_path = tmp_path / "app"
    repo_path.mkdir()

    monkeypatch.setattr(
        router.session_store,
        "get",
        lambda session_id: {
            "session_id": session_id,
            "workspace": str(repo_path.parent),
            "created_at": "now",
            "last_access": "now",
            "user_id": "zhaojindong",
            "metadata": {
                "workspace_id": "ws-1",
                "repo_name": "app",
                "branch": "main",
                "session_repo_path": str(repo_path),
                "user_id": "zhaojindong",
            },
        },
    )
    monkeypatch.setattr(router, "_is_query_active", lambda session_id: False)
    monkeypatch.setattr(router, "resolve_session_repo_path", lambda session_id: repo_path)
    monkeypatch.setattr(router, "commit_message_context", lambda path: "## status\n M app.py")

    async def fail_generate(path, context):
        raise RuntimeError("AI unavailable")

    monkeypatch.setattr(router, "generate_commit_message", fail_generate)

    response = await router.suggest_session_commit_message("sess-1")

    assert response.message == "Update app"
    assert response.generated is False


@pytest.mark.asyncio
async def test_session_git_push_uses_session_branch_and_current_user(monkeypatch, tmp_path):
    repo_path = tmp_path / "app"
    repo_path.mkdir()
    calls = []

    monkeypatch.setattr(
        router.session_store,
        "get",
        lambda session_id: {
            "session_id": session_id,
            "workspace": str(repo_path.parent),
            "created_at": "now",
            "last_access": "now",
            "user_id": "zhaojindong",
            "metadata": {
                "workspace_id": "ws-1",
                "repo_name": "app",
                "branch": "feature/x",
                "session_repo_path": str(repo_path),
                "user_id": "zhaojindong",
            },
        },
    )
    monkeypatch.setattr(router, "_is_query_active", lambda session_id: False)
    monkeypatch.setattr(router, "resolve_session_repo_path", lambda session_id: repo_path)

    def fake_push(path, branch=None, user_id=None):
        calls.append((path, branch, user_id))
        return SimpleNamespace(to_dict=lambda: {"status": "pushed", "branch": branch, "stdout": "", "stderr": ""})

    monkeypatch.setattr(router, "git_push", fake_push)

    response = await router.push_session_changes("sess-1")

    assert calls == [(repo_path, "feature/x", "zhaojindong")]
    assert response.status == "pushed"
    assert response.branch == "feature/x"


def test_agent_rejects_unbound_session(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "src.core.agent.session_store.get",
        lambda session_id: {
            "session_id": session_id,
            "workspace": str(tmp_path),
            "metadata": {},
        },
    )

    with pytest.raises(RuntimeError, match="not bound"):
        _resolve_cwd("legacy")


def test_agent_cwd_resolves_to_bound_repo_local_path(monkeypatch, tmp_path):
    repo_path = tmp_path / "ws-1" / "creation-tool"
    repo_path.mkdir(parents=True)
    monkeypatch.setattr(
        "src.core.agent.session_store.get",
        lambda session_id: {
            "session_id": session_id,
            "workspace": str(tmp_path / "ws-1"),
            "metadata": {
                "workspace_id": "ws-1",
                "repo_name": "creation-tool",
                "branch": "dev_temp",
            },
        },
    )
    monkeypatch.setattr(
        "src.core.agent.workspace_store.get",
        lambda workspace_id: {
            "workspace_id": workspace_id,
            "cwd": str(tmp_path / "ws-1"),
            "repos": [
                {
                    "name": "creation-tool",
                    "branch": "dev_temp",
                    "local_path": str(repo_path),
                }
            ],
        },
    )

    assert _resolve_cwd("sess-1") == repo_path


def test_agent_cwd_prefers_session_repo_path(monkeypatch, tmp_path):
    repo_path = tmp_path / "ws-1" / ".session-worktrees" / "sess-1" / "creation-tool"
    repo_path.mkdir(parents=True)
    monkeypatch.setattr(
        "src.core.agent.session_store.get",
        lambda session_id: {
            "session_id": session_id,
            "workspace": str(repo_path.parent),
            "metadata": {
                "workspace_id": "ws-1",
                "repo_name": "creation-tool",
                "branch": "dev_temp",
                "session_repo_path": str(repo_path),
            },
        },
    )

    assert _resolve_cwd("sess-1") == repo_path


def test_worktree_remove_checks_return_code_and_prunes_on_failure(monkeypatch, tmp_path, caplog):
    repo_path = tmp_path / "ws-1" / "app"
    source_repo = tmp_path / ".sources" / "app"
    repo_path.mkdir(parents=True)
    source_repo.mkdir(parents=True)
    commands = []

    class FakeResult:
        def __init__(self, returncode, stdout="", stderr=""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(cmd, cwd, capture_output, text, timeout):
        commands.append((cmd, cwd))
        if cmd[:3] == ["git", "worktree", "remove"]:
            return FakeResult(1, stderr="fatal: stale worktree metadata")
        return FakeResult(0)

    monkeypatch.setattr(workspace.settings, "workspace_root", str(tmp_path))
    monkeypatch.setattr(workspace.subprocess, "run", fake_run)

    store = workspace.WorkspaceStore()
    with caplog.at_level("WARNING"):
        store._remove_worktree(repo_path)

    assert commands == [
        (["git", "worktree", "remove", "--force", str(repo_path)], str(source_repo)),
        (["git", "worktree", "prune"], str(source_repo)),
    ]
    assert "Failed to remove git worktree" in caplog.text


def test_workspace_creates_session_specific_worktree(monkeypatch, tmp_path):
    monkeypatch.setattr(workspace.settings, "workspace_root", str(tmp_path))
    store = workspace.WorkspaceStore()
    ws_id = "ws-1"
    ws_dir = tmp_path / ws_id
    ws_dir.mkdir()
    store._path(ws_id).write_text(
        json.dumps(
            {
                "workspace_id": ws_id,
                "name": "test",
                "cwd": str(ws_dir),
                "repos": [{"name": "app", "url": "https://example.com/app.git", "branch": "main"}],
            }
        )
    )
    calls = []

    def fake_create_worktree(url, source_dir, worktree_path, branch=None, user_id=None):
        calls.append((url, source_dir, worktree_path, branch, user_id))
        return SimpleNamespace(local_path=worktree_path)

    monkeypatch.setattr(workspace, "create_worktree", fake_create_worktree)

    repo = store.create_session_worktree(ws_id, "app", "sess-1", "feature/x")

    assert repo.local_path == ws_dir / ".session-worktrees" / "sess-1" / "app"
    assert calls == [
        (
            "https://example.com/app.git",
            tmp_path / ".sources",
            ws_dir / ".session-worktrees" / "sess-1" / "app",
            "feature/x",
            "zhaojindong",
        )
    ]


def test_list_branches_uses_remote_source(monkeypatch, tmp_path):
    """Branch dropdown must reflect origin only — never local clone refs."""
    monkeypatch.setattr(workspace.settings, "workspace_root", str(tmp_path))
    store = workspace.WorkspaceStore()
    ws_id = "ws-1"
    ws_dir = tmp_path / ws_id
    ws_dir.mkdir()
    store._path(ws_id).write_text(
        json.dumps(
            {
                "workspace_id": ws_id,
                "name": "test",
                "cwd": str(ws_dir),
                "user_id": "alice",
                "repos": [{"name": "app", "url": "https://example.com/app.git", "branch": "main"}],
            }
        )
    )

    calls = []

    def fake_remote_branches(url, user_id=None):
        calls.append((url, user_id))
        return ["dev", "main"]

    monkeypatch.setattr(workspace, "git_remote_branches", fake_remote_branches)

    assert store.list_branches(ws_id, "app") == ["dev", "main"]
    assert calls == [("https://example.com/app.git", "alice")]


def test_list_branches_returns_remote_result_verbatim(monkeypatch, tmp_path):
    """The list comes straight from the remote, even when empty — no local fallback."""
    monkeypatch.setattr(workspace.settings, "workspace_root", str(tmp_path))
    store = workspace.WorkspaceStore()
    ws_id = "ws-1"
    ws_dir = tmp_path / ws_id
    ws_dir.mkdir()
    store._path(ws_id).write_text(
        json.dumps(
            {
                "workspace_id": ws_id,
                "name": "test",
                "cwd": str(ws_dir),
                "repos": [{"name": "app", "url": "https://example.com/app.git", "branch": "main"}],
            }
        )
    )

    monkeypatch.setattr(workspace, "git_remote_branches", lambda url, user_id=None: [])

    assert store.list_branches(ws_id, "app") == []


def test_workspace_store_backfills_legacy_user(monkeypatch, tmp_path):
    monkeypatch.setattr(workspace.settings, "workspace_root", str(tmp_path))
    store_dir = tmp_path / ".workspaces"
    store_dir.mkdir()
    record_path = store_dir / "ws-1.json"
    record_path.write_text(
        json.dumps(
            {
                "workspace_id": "ws-1",
                "name": "legacy",
                "cwd": str(tmp_path / "ws-1"),
                "repos": [],
                "created_at": "now",
                "updated_at": "now",
            }
        ),
        encoding="utf-8",
    )

    workspace.WorkspaceStore()

    assert json.loads(record_path.read_text())["user_id"] == "zhaojindong"


def test_session_history_is_persisted_under_workspace_and_deleted(monkeypatch, tmp_path):
    monkeypatch.setattr(session.settings, "workspace_root", str(tmp_path / "runtime-workspaces"))
    store = session.SessionStore()
    workspace_dir = tmp_path / "ws-1"
    session_id = store.create(
        workspace_dir=str(workspace_dir),
        metadata={"workspace_id": "ws-1", "repo_name": "app", "branch": "main"},
    )

    store.append_message(session_id, {"type": "user", "prompt": "第一轮"})
    store.append_message(session_id, {"type": "assistant", "content": [{"type": "text", "text": "好的"}]})

    history_path = workspace_dir / ".session-history" / f"{session_id}.jsonl"
    assert history_path.exists()
    assert [entry["message"]["type"] for entry in store.list_messages(session_id)] == [
        "user",
        "assistant",
    ]

    store.delete(session_id)

    assert not history_path.exists()
    assert not store._path(session_id).exists()


def test_session_store_backfills_legacy_user(monkeypatch, tmp_path):
    monkeypatch.setattr(session.settings, "workspace_root", str(tmp_path))
    store_dir = tmp_path / ".sessions"
    store_dir.mkdir()
    record_path = store_dir / "sess-1.json"
    record_path.write_text(
        json.dumps(
            {
                "session_id": "sess-1",
                "workspace": str(tmp_path / "ws-1"),
                "created_at": "now",
                "last_access": "now",
                "metadata": {"workspace_id": "ws-1"},
            }
        ),
        encoding="utf-8",
    )

    session.SessionStore()

    record = json.loads(record_path.read_text())
    assert record["user_id"] == "zhaojindong"
    assert record["metadata"]["user_id"] == "zhaojindong"
