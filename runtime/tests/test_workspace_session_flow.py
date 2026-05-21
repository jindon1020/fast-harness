import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from src.api import router
from src.api.schemas import SessionCreateRequest, WorkspaceCreateRequest
from src.core.agent import _resolve_cwd


def test_workspace_creation_defaults_to_creation_tool_repo():
    request = WorkspaceCreateRequest(name="repo-ws", branch="feature/x")

    assert request.repo_url is None
    assert request.repo_name is None
    assert request.branch == "feature/x"


def test_session_creation_requires_workspace():
    with pytest.raises(ValidationError):
        SessionCreateRequest()


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
    monkeypatch.setattr(router, "run_query_stream", fake_run_query_stream)

    response = await router.query_session("sess-1", router.QueryRequest(prompt="hi"))
    async for _event in response.body_iterator:
        break

    assert fake_workspace_store.checked_out == ("ws-1", "app", "main")


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
