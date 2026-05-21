import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from src.api import router
from src.api.schemas import (
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

        def create(self, name, repositories):
            self.created = (name, repositories)
            return {
                "workspace_id": "ws-1",
                "name": name,
                "cwd": "/tmp/ws-1",
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
            self.checked_out = None

        def get(self, workspace_id):
            assert workspace_id == "ws-1"
            return {
                "workspace_id": "ws-1",
                "cwd": str(tmp_path),
                "repos": [{"name": "app", "branch": "main"}],
            }

        def checkout_branch(self, workspace_id, repo_name, branch):
            self.checked_out = (workspace_id, repo_name, branch)
            return {"repo": repo_name, "branch": branch, "status": "ok"}

    class FakeSessionStore:
        def __init__(self):
            self.metadata = None

        def create(self, *, workspace_dir, metadata):
            self.metadata = metadata
            return "sess-1"

        def get(self, session_id):
            assert session_id == "sess-1"
            return {
                "session_id": "sess-1",
                "workspace": str(tmp_path),
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

    assert response.session_id == "sess-1"
    assert fake_workspace_store.checked_out == ("ws-1", "app", "feature/x")
    assert fake_session_store.metadata == {
        "workspace_id": "ws-1",
        "repo_name": "app",
        "branch": "feature/x",
    }


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
