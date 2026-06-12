import json
import asyncio

import pytest
from types import SimpleNamespace
from fastapi import HTTPException
from pydantic import ValidationError

from src.api import router
from src.api.schemas import (
    BugPipelineApprovalRequest,
    BugPipelineCreateRequest,
    BugPipelineStepRunRequest,
    BugPipelineTerminateRequest,
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


def bug_pipeline_request(**overrides):
    payload = {
        "repo_key": "app",
        "target_branch": "feature/sp11",
        "namespace": "drama-dev",
        "affected_api": "GET /api/projects",
        "problem_description": "列表接口返回 500",
        "expected_result": "返回项目列表",
        "actual_result": "返回 500",
        "reviewer_id": "reviewer",
    }
    payload.update(overrides)
    return BugPipelineCreateRequest(**payload)


class FakeBugPipelineStore:
    def __init__(self):
        self.records = {}

    def create(self, record):
        steps = {
            step: {
                "id": step,
                "title": step,
                "status": "pending",
                "attempts": 0,
                "started_at": None,
                "completed_at": None,
                "summary": "",
            }
            for step in router.PIPELINE_STEPS
        }
        record = {
            **record,
            "status": "pending",
            "approval_status": record.get("approval_status", "not_required"),
            "code_approval_status": record.get("code_approval_status", "not_required"),
            "review_retry_count": 0,
            "steps": steps,
            "events": [],
            "created_at": "now",
            "updated_at": "now",
        }
        self.records[record["pipeline_id"]] = record
        return record

    def require(self, pipeline_id):
        return self.records[pipeline_id]

    def list_all(self):
        return list(self.records.values())

    def update(self, pipeline_id, patch):
        self.records[pipeline_id].update(patch)
        return self.records[pipeline_id]

    def rename(self, pipeline_id, name):
        self.records[pipeline_id]["display_name"] = name.strip()
        return self.records[pipeline_id]

    def delete(self, pipeline_id):
        self.records.pop(pipeline_id, None)

    def set_step(self, pipeline_id, step, status, summary=""):
        item = self.records[pipeline_id]["steps"][step]
        item["status"] = status
        item["summary"] = summary
        if status == "running":
            item["attempts"] += 1
        return self.records[pipeline_id]

    def append_event(self, pipeline_id, event):
        self.records[pipeline_id]["events"].append(event)
        return self.records[pipeline_id]

    def terminate(self, pipeline_id, user_id, reason=""):
        record = self.records[pipeline_id]
        for step in record["steps"].values():
            if step["status"] in {"pending", "running", "waiting_approval"}:
                step["status"] = "skipped"
                step["summary"] = "流水线已终止"
        record["status"] = "terminated"
        record["terminated_by"] = user_id
        record["termination_reason"] = reason
        return record


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
async def test_bug_pipeline_requires_remote_feature_branch(monkeypatch):
    repo = {
        "key": "app",
        "name": "app-service",
        "url": "https://example.com/app.git",
        "default_branch": "main",
        "enabled": True,
    }
    monkeypatch.setattr(type(router.settings), "get_repository", lambda self, key: repo)
    monkeypatch.setattr(type(router.settings), "get_user", lambda self, user_id: {"id": user_id, "name": user_id, "role": "member", "enabled": True})
    monkeypatch.setattr(router, "remote_branches", lambda url, user_id=None: ["main", "feature/other"])

    with pytest.raises(HTTPException) as exc_info:
        await router.create_bug_pipeline(bug_pipeline_request(target_branch="feature/sp11"))

    assert exc_info.value.status_code == 400
    assert "不存在于远端" in exc_info.value.detail


@pytest.mark.asyncio
async def test_bug_pipeline_rejects_non_feature_branch(monkeypatch):
    repo = {
        "key": "app",
        "name": "app-service",
        "url": "https://example.com/app.git",
        "default_branch": "main",
        "enabled": True,
    }
    monkeypatch.setattr(type(router.settings), "get_repository", lambda self, key: repo)
    monkeypatch.setattr(type(router.settings), "get_user", lambda self, user_id: {"id": user_id, "name": user_id, "role": "member", "enabled": True})

    with pytest.raises(HTTPException) as exc_info:
        await router.create_bug_pipeline(bug_pipeline_request(target_branch="dev"))

    assert exc_info.value.status_code == 400
    assert "feature/*" in exc_info.value.detail


@pytest.mark.asyncio
async def test_bug_pipeline_uses_target_feature_branch_directly(monkeypatch, tmp_path):
    repo_path = tmp_path / "ws-1" / ".session-worktrees" / "sess-1" / "app-service"
    repo_path.mkdir(parents=True)
    created_workspaces = []
    session_meta = {}

    class FakeWorkspaceStore:
        def create(self, name, repositories, user_id=None, git_user_id=None):
            created_workspaces.append((name, repositories, user_id, git_user_id))
            return {
                "workspace_id": "ws-1",
                "name": name,
                "cwd": str(tmp_path / "ws-1"),
                "repos": repositories,
                "created_at": "now",
                "updated_at": "now",
                "user_id": user_id,
            }

        def create_session_worktree(
            self,
            workspace_id,
            repo_name,
            session_id,
            branch,
            user_id=None,
            git_user_id=None,
            install_harness=True,
        ):
            assert branch == "feature/sp11"
            assert user_id == "zhaojindong"
            assert git_user_id == "zhaojindong"
            assert install_harness is True
            return SimpleNamespace(local_path=repo_path)

        def remove_session_worktree(self, repo_path):
            raise AssertionError("should not remove successful worktree")

        def delete(self, workspace_id):
            raise AssertionError("should not delete successful workspace")

    class FakeSessionStore:
        def create(self, *, workspace_dir, metadata, session_id=None, user_id=None):
            session_meta.update(metadata)
            return session_id

    repo = {
        "key": "app",
        "name": "app-service",
        "url": "https://example.com/app.git",
        "default_branch": "main",
        "enabled": True,
    }

    fake_pipeline_store = FakeBugPipelineStore()
    monkeypatch.setattr(router, "workspace_store", FakeWorkspaceStore())
    monkeypatch.setattr(router, "session_store", FakeSessionStore())
    monkeypatch.setattr(router, "bug_pipeline_store", fake_pipeline_store)
    monkeypatch.setattr(type(router.settings), "get_repository", lambda self, key: repo)
    monkeypatch.setattr(type(router.settings), "get_user", lambda self, user_id: {"id": user_id, "name": user_id, "role": "member", "enabled": True})
    monkeypatch.setattr(router, "remote_branches", lambda url, user_id=None: ["feature/sp11"])

    response = await router.create_bug_pipeline(
        bug_pipeline_request(
            screenshot_notes="红框内接口报错",
            screenshot_images=[
                {
                    "name": "error.png",
                    "mime_type": "image/png",
                    "data": "iVBORw0KGgo=",
                    "size": 8,
                }
            ],
        )
    )

    assert created_workspaces[0][1][0]["branch"] == "feature/sp11"
    assert created_workspaces[0][1][0]["install_harness"] is False
    assert session_meta["target_branch"] == "feature/sp11"
    assert session_meta["branch"] == "feature/sp11"
    assert response.bugfix_branch == "feature/sp11"
    assert response.steps["intake"].status == "passed"
    assert response.screenshot_attachments[0]["name"] == "error.png"
    screenshot_path = repo_path / response.screenshot_attachments[0]["path"]
    assert screenshot_path.exists()
    bug_report = (repo_path / ".ai" / "dev-fix" / response.pipeline_id / "bug_report.md").read_text(encoding="utf-8")
    assert "## 问题截图" in bug_report
    assert response.screenshot_attachments[0]["path"] in bug_report


@pytest.mark.asyncio
async def test_reporter_bug_pipeline_uses_reviewer_git_credentials(monkeypatch, tmp_path):
    repo_path = tmp_path / "ws-1" / ".session-worktrees" / "sess-1" / "app-service"
    repo_path.mkdir(parents=True)
    workspace_calls = []
    session_worktree_calls = []
    remote_branch_user_ids = []

    class FakeWorkspaceStore:
        def create(self, name, repositories, user_id=None, git_user_id=None):
            workspace_calls.append((name, repositories, user_id, git_user_id))
            return {
                "workspace_id": "ws-1",
                "name": name,
                "cwd": str(tmp_path / "ws-1"),
                "repos": repositories,
                "created_at": "now",
                "updated_at": "now",
                "user_id": user_id,
            }

        def create_session_worktree(
            self,
            workspace_id,
            repo_name,
            session_id,
            branch,
            user_id=None,
            git_user_id=None,
            install_harness=True,
        ):
            session_worktree_calls.append((workspace_id, repo_name, branch, user_id, git_user_id, install_harness))
            return SimpleNamespace(local_path=repo_path)

        def remove_session_worktree(self, repo_path):
            raise AssertionError("should not remove successful worktree")

        def delete(self, workspace_id):
            raise AssertionError("should not delete successful workspace")

    class FakeSessionStore:
        def create(self, *, workspace_dir, metadata, session_id=None, user_id=None):
            assert metadata["user_id"] == "qa01"
            assert user_id == "qa01"
            return session_id

    repo = {
        "key": "app",
        "name": "app-service",
        "url": "https://example.com/app.git",
        "default_branch": "main",
        "enabled": True,
    }
    roles = {
        "qa01": "reporter",
        "reviewer": "member",
    }

    fake_pipeline_store = FakeBugPipelineStore()
    monkeypatch.setattr(router, "workspace_store", FakeWorkspaceStore())
    monkeypatch.setattr(router, "session_store", FakeSessionStore())
    monkeypatch.setattr(router, "bug_pipeline_store", fake_pipeline_store)
    monkeypatch.setattr(type(router.settings), "get_repository", lambda self, key: repo)
    monkeypatch.setattr(type(router.settings), "get_user", lambda self, user_id: {"id": user_id, "name": user_id, "role": roles[user_id], "enabled": True})
    monkeypatch.setattr(router, "remote_branches", lambda url, user_id=None: remote_branch_user_ids.append(user_id) or ["feature/sp11"])
    response = await router.create_bug_pipeline(bug_pipeline_request(), x_user_id="qa01")

    assert response.user_id == "qa01"
    assert remote_branch_user_ids == ["reviewer"]
    assert workspace_calls[0][2:] == ("qa01", "reviewer")
    assert session_worktree_calls[0][3:] == ("qa01", "reviewer", True)


@pytest.mark.asyncio
async def test_bug_pipeline_creates_related_repo_context_worktrees(monkeypatch, tmp_path):
    primary_path = tmp_path / "ws-1" / ".session-worktrees" / "sess-1" / "creation-tool"
    related_path = tmp_path / "ws-1" / ".session-worktrees" / "sess-1" / "algo-manager"
    primary_path.mkdir(parents=True)
    related_path.mkdir(parents=True)
    created_repositories = []
    session_worktrees = []
    session_meta = {}
    remote_checks = []

    class FakeWorkspaceStore:
        def create(self, name, repositories, user_id=None, git_user_id=None):
            created_repositories.extend(repositories)
            return {
                "workspace_id": "ws-1",
                "name": name,
                "cwd": str(tmp_path / "ws-1"),
                "repos": repositories,
                "created_at": "now",
                "updated_at": "now",
                "user_id": user_id,
            }

        def create_session_worktree(
            self,
            workspace_id,
            repo_name,
            session_id,
            branch,
            user_id=None,
            git_user_id=None,
            install_harness=True,
        ):
            session_worktrees.append((repo_name, branch, user_id, git_user_id, install_harness))
            if repo_name == "creation-tool":
                return SimpleNamespace(local_path=primary_path)
            return SimpleNamespace(local_path=related_path)

        def remove_session_worktree(self, repo_path):
            raise AssertionError("should not remove successful worktree")

        def delete(self, workspace_id):
            raise AssertionError("should not delete successful workspace")

    class FakeSessionStore:
        def create(self, *, workspace_dir, metadata, session_id=None, user_id=None):
            session_meta.update(metadata)
            return session_id

    repos = {
        "app": {
            "key": "app",
            "name": "creation-tool",
            "url": "https://example.com/creation-tool.git",
            "default_branch": "dev",
            "enabled": True,
        },
        "algo": {
            "key": "algo",
            "name": "algo-manager",
            "url": "https://example.com/algo-manager.git",
            "default_branch": "dev",
            "enabled": True,
        },
    }

    fake_pipeline_store = FakeBugPipelineStore()
    monkeypatch.setattr(router, "workspace_store", FakeWorkspaceStore())
    monkeypatch.setattr(router, "session_store", FakeSessionStore())
    monkeypatch.setattr(router, "bug_pipeline_store", fake_pipeline_store)
    monkeypatch.setattr(type(router.settings), "get_repository", lambda self, key: repos[key])
    monkeypatch.setattr(type(router.settings), "get_user", lambda self, user_id: {"id": user_id, "name": user_id, "role": "member", "enabled": True})
    monkeypatch.setattr(router, "remote_branches", lambda url, user_id=None: remote_checks.append((url, user_id)) or ["feature/sp11", "dev"])
    response = await router.create_bug_pipeline(
        bug_pipeline_request(
            repo_contexts=[
                {
                    "repo_key": "app",
                    "branch": "feature/sp11",
                    "role": "fix",
                    "correlation_id_name": "request_id",
                    "correlation_id_value": "req-1",
                },
                {
                    "repo_key": "algo",
                    "branch": "dev",
                    "role": "observe",
                    "correlation_id_name": "task_id",
                    "correlation_id_value": "task-9",
                },
            ]
        )
    )

    assert [repo["name"] for repo in created_repositories] == ["creation-tool", "algo-manager"]
    assert [repo["install_harness"] for repo in created_repositories] == [False, False]
    assert session_worktrees == [
        ("creation-tool", "feature/sp11", "zhaojindong", "zhaojindong", True),
        ("algo-manager", "dev", "zhaojindong", "zhaojindong", False),
    ]
    assert session_meta["related_repo_paths"] == {"algo-manager": str(related_path)}
    assert response.repo_contexts[0]["correlation_id_value"] == "req-1"
    assert response.repo_contexts[1]["correlation_id_name"] == "task_id"
    assert "task_id `task-9`" in (primary_path / ".ai" / "dev-fix" / response.pipeline_id / "bug_report.md").read_text(encoding="utf-8")
    assert len(remote_checks) == 2


@pytest.mark.asyncio
async def test_bug_pipeline_rejects_reporter_as_reviewer(monkeypatch):
    repo = {
        "key": "app",
        "name": "app-service",
        "url": "https://example.com/app.git",
        "default_branch": "main",
        "enabled": True,
    }
    roles = {
        "zhaojindong": "admin",
        "qa01": "reporter",
    }

    monkeypatch.setattr(type(router.settings), "get_repository", lambda self, key: repo)
    monkeypatch.setattr(type(router.settings), "get_user", lambda self, user_id: {"id": user_id, "name": user_id, "role": roles[user_id], "enabled": True})

    with pytest.raises(HTTPException) as exc_info:
        await router.create_bug_pipeline(bug_pipeline_request(reviewer_id="qa01"), x_user_id="zhaojindong")

    assert exc_info.value.status_code == 400
    assert "member 或 admin" in exc_info.value.detail


@pytest.mark.asyncio
async def test_bug_pipeline_approval_requires_reviewer_or_admin(monkeypatch):
    fake_store = FakeBugPipelineStore()
    record = fake_store.create(
        {
            "pipeline_id": "bug-1",
            "user_id": "tester",
            "reviewer_id": "reviewer",
            "repo_key": "app",
            "repo_name": "app",
            "workspace_id": "ws-1",
            "session_id": "sess-1",
            "target_branch": "feature/sp11",
            "bugfix_branch": "bugfix/bug-1-fix",
            "git_user_id": "reviewer",
            "namespace": "drama-dev",
            "affected_api": "GET /x",
            "problem_description": "bug",
            "expected_result": "ok",
            "actual_result": "fail",
            "artifact_dir": ".ai/dev-fix/bug-1",
        }
    )
    record["steps"]["fix_plan"]["status"] = "waiting_approval"
    monkeypatch.setattr(router, "bug_pipeline_store", fake_store)

    def fake_get_user(user_id):
        return {"id": user_id, "name": user_id, "role": "member", "enabled": True}

    monkeypatch.setattr(type(router.settings), "get_user", lambda self, user_id: fake_get_user(user_id))
    monkeypatch.setattr(type(router.settings), "is_admin", lambda self, user_id: False)

    with pytest.raises(HTTPException) as exc_info:
        await router.approve_bug_pipeline(
            "bug-1",
            BugPipelineApprovalRequest(approved=True),
            x_user_id="tester",
        )

    assert exc_info.value.status_code == 403

    response = await router.approve_bug_pipeline(
        "bug-1",
        BugPipelineApprovalRequest(approved=True, comment="ok"),
        x_user_id="reviewer",
    )

    assert response.approval_status == "approved"
    assert response.steps["fix_plan"].status == "passed"


@pytest.mark.asyncio
async def test_bug_pipeline_reporter_can_terminate_pipeline(monkeypatch):
    fake_store = FakeBugPipelineStore()
    record = fake_store.create(
        {
            "pipeline_id": "bug-1",
            "user_id": "tester",
            "reviewer_id": "reviewer",
            "repo_key": "app",
            "repo_name": "app",
            "workspace_id": "ws-1",
            "session_id": "sess-1",
            "target_branch": "feature/sp11",
            "bugfix_branch": "bugfix/bug-1-fix",
            "namespace": "drama-dev",
            "affected_api": "GET /x",
            "problem_description": "bug",
            "expected_result": "ok",
            "actual_result": "fail",
            "artifact_dir": ".ai/dev-fix/bug-1",
        }
    )
    record["steps"]["intake"]["status"] = "passed"
    record["steps"]["root_cause"]["status"] = "passed"
    record["steps"]["fix_plan"]["status"] = "pending"
    monkeypatch.setattr(router, "bug_pipeline_store", fake_store)
    monkeypatch.setattr(router, "_active_queries", {})
    monkeypatch.setattr(type(router.settings), "get_user", lambda self, user_id: {"id": user_id, "name": user_id, "role": "reporter", "enabled": True})
    monkeypatch.setattr(type(router.settings), "is_admin", lambda self, user_id: False)

    response = await router.terminate_bug_pipeline(
        "bug-1",
        BugPipelineTerminateRequest(reason="不是代码 bug"),
        x_user_id="tester",
    )

    assert response.status == "terminated"
    assert response.terminated_by == "tester"
    assert response.termination_reason == "不是代码 bug"
    assert response.steps["intake"].status == "passed"
    assert response.steps["root_cause"].status == "passed"
    assert response.steps["fix_plan"].status == "skipped"
    assert response.steps["code_generation"].status == "skipped"

    with pytest.raises(HTTPException) as exc_info:
        await router.run_bug_pipeline_step("bug-1", "fix_plan", x_user_id="tester")

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_bug_pipeline_sidebar_session_can_be_renamed_and_deleted(monkeypatch):
    fake_store = FakeBugPipelineStore()
    fake_store.create(
        {
            "pipeline_id": "bug-1",
            "user_id": "tester",
            "reviewer_id": "reviewer",
            "repo_key": "app",
            "repo_name": "app",
            "workspace_id": "ws-1",
            "session_id": "sess-1",
            "target_branch": "feature/sp11",
            "bugfix_branch": "feature/sp11",
            "namespace": "drama-dev",
            "affected_api": "GET /x",
            "problem_description": "接口报错",
            "expected_result": "ok",
            "actual_result": "fail",
            "artifact_dir": ".ai/dev-fix/bug-1",
        }
    )
    deleted_sessions = []

    class FakeSessionStore:
        def delete(self, session_id):
            deleted_sessions.append(session_id)

    monkeypatch.setattr(router, "bug_pipeline_store", fake_store)
    monkeypatch.setattr(router, "session_store", FakeSessionStore())
    monkeypatch.setattr(router, "_active_queries", {})
    monkeypatch.setattr(type(router.settings), "get_user", lambda self, user_id: {"id": user_id, "name": user_id, "role": "reporter", "enabled": True})
    monkeypatch.setattr(type(router.settings), "is_admin", lambda self, user_id: False)

    renamed = await router.rename_bug_pipeline(
        "bug-1",
        RenameRequest(name="图片生成 project_id 问题"),
        x_user_id="tester",
    )

    assert renamed.display_name == "图片生成 project_id 问题"
    assert fake_store.records["bug-1"]["display_name"] == "图片生成 project_id 问题"

    deleted = await router.delete_bug_pipeline("bug-1", x_user_id="tester")

    assert deleted == {"status": "deleted", "pipeline_id": "bug-1"}
    assert "bug-1" not in fake_store.records
    assert deleted_sessions == ["sess-1"]


@pytest.mark.asyncio
async def test_bug_pipeline_can_skip_quality_gate_steps_individually(monkeypatch):
    fake_store = FakeBugPipelineStore()
    record = fake_store.create(
        {
            "pipeline_id": "bug-1",
            "user_id": "tester",
            "reviewer_id": "reviewer",
            "repo_key": "app",
            "repo_name": "app",
            "workspace_id": "ws-1",
            "session_id": "sess-1",
            "target_branch": "feature/sp11",
            "bugfix_branch": "bugfix/bug-1-fix",
            "namespace": "drama-dev",
            "affected_api": "GET /x",
            "problem_description": "bug",
            "expected_result": "ok",
            "actual_result": "fail",
            "artifact_dir": ".ai/dev-fix/bug-1",
        }
    )
    for step in ["intake", "root_cause", "fix_plan", "code_generation"]:
        record["steps"][step]["status"] = "passed"
    monkeypatch.setattr(router, "bug_pipeline_store", fake_store)
    monkeypatch.setattr(router, "_active_queries", {})
    async def fake_start_step(pipeline_id, step):
        return fake_store.require(pipeline_id)

    monkeypatch.setattr(router, "_start_bug_pipeline_step", fake_start_step)
    monkeypatch.setattr(type(router.settings), "get_user", lambda self, user_id: {"id": user_id, "name": user_id, "role": "reporter", "enabled": True})
    monkeypatch.setattr(type(router.settings), "is_admin", lambda self, user_id: False)

    first = await router.skip_bug_pipeline_step(
        "bug-1",
        "code_review",
        BugPipelineStepRunRequest(note="skip review"),
        x_user_id="tester",
    )
    second = await router.skip_bug_pipeline_step(
        "bug-1",
        "unit_test",
        BugPipelineStepRunRequest(note="skip unit test"),
        x_user_id="tester",
    )
    third = await router.skip_bug_pipeline_step(
        "bug-1",
        "regression",
        BugPipelineStepRunRequest(note="skip regression"),
        x_user_id="tester",
    )

    assert first.steps["code_review"].status == "skipped"
    assert second.steps["unit_test"].status == "skipped"
    assert third.steps["regression"].status == "skipped"
    router._ensure_pipeline_code_ready(fake_store.require("bug-1"))


@pytest.mark.asyncio
async def test_bug_pipeline_code_approval_and_git_actions_require_developer(monkeypatch, tmp_path):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    fake_store = FakeBugPipelineStore()
    record = fake_store.create(
        {
            "pipeline_id": "bug-1",
            "user_id": "tester",
            "reviewer_id": "reviewer",
            "repo_key": "app",
            "repo_name": "app",
            "workspace_id": "ws-1",
            "session_id": "sess-1",
            "target_branch": "feature/sp11",
            "bugfix_branch": "bugfix/bug-1-fix",
            "namespace": "drama-dev",
            "affected_api": "GET /x",
            "problem_description": "bug",
            "expected_result": "ok",
            "actual_result": "fail",
            "artifact_dir": ".ai/dev-fix/bug-1",
        }
    )
    record["steps"]["regression"]["status"] = "passed"
    monkeypatch.setattr(router, "bug_pipeline_store", fake_store)
    monkeypatch.setattr(router, "resolve_session_repo_path", lambda session_id: repo_path)
    monkeypatch.setattr(router, "_is_query_active", lambda session_id: False)
    monkeypatch.setattr(type(router.settings), "is_admin", lambda self, user_id: user_id == "admin")

    def fake_get_user(user_id):
        roles = {"tester": "reporter", "reviewer": "member", "admin": "admin"}
        return {"id": user_id, "name": user_id, "role": roles[user_id], "enabled": True}

    monkeypatch.setattr(type(router.settings), "get_user", lambda self, user_id: fake_get_user(user_id))

    with pytest.raises(HTTPException) as exc_info:
        await router.approve_bug_pipeline_code(
            "bug-1",
            BugPipelineApprovalRequest(approved=True),
            x_user_id="tester",
        )

    assert exc_info.value.status_code == 403

    approved = await router.approve_bug_pipeline_code(
        "bug-1",
        BugPipelineApprovalRequest(approved=True, comment="ship it"),
        x_user_id="reviewer",
    )

    assert approved.code_approval_status == "approved"
    assert approved.code_approved_by == "reviewer"

    commit_calls = []
    push_calls = []

    def fake_commit(path, message, user_id=None):
        commit_calls.append((path, message, user_id))
        return SimpleNamespace(to_dict=lambda: {"status": "committed", "branch": "feature/sp11", "stdout": "ok", "stderr": ""}, status="committed", branch="feature/sp11")

    def fake_push(path, branch=None, user_id=None):
        push_calls.append((path, branch, user_id))
        return SimpleNamespace(to_dict=lambda: {"status": "pushed", "branch": branch, "stdout": "", "stderr": ""}, status="pushed", branch=branch)

    monkeypatch.setattr(router, "git_commit_all", fake_commit)
    monkeypatch.setattr(router, "git_push", fake_push)

    commit_response = await router.commit_bug_pipeline_changes(
        "bug-1",
        GitCommitRequest(message="fix project list"),
        x_user_id="reviewer",
    )
    push_response = await router.push_bug_pipeline_changes("bug-1", x_user_id="reviewer")

    assert commit_calls == [(repo_path, "fix project list", "reviewer")]
    assert push_calls == [(repo_path, "feature/sp11", "reviewer")]
    assert commit_response.status == "committed"
    assert push_response.status == "pushed"


@pytest.mark.asyncio
async def test_bug_pipeline_git_commit_requires_code_approval(monkeypatch, tmp_path):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    fake_store = FakeBugPipelineStore()
    record = fake_store.create(
        {
            "pipeline_id": "bug-1",
            "user_id": "tester",
            "reviewer_id": "reviewer",
            "repo_key": "app",
            "repo_name": "app",
            "workspace_id": "ws-1",
            "session_id": "sess-1",
            "target_branch": "feature/sp11",
            "bugfix_branch": "bugfix/bug-1-fix",
            "namespace": "drama-dev",
            "affected_api": "GET /x",
            "problem_description": "bug",
            "expected_result": "ok",
            "actual_result": "fail",
            "artifact_dir": ".ai/dev-fix/bug-1",
        }
    )
    record["steps"]["regression"]["status"] = "passed"
    monkeypatch.setattr(router, "bug_pipeline_store", fake_store)
    monkeypatch.setattr(router, "resolve_session_repo_path", lambda session_id: repo_path)
    monkeypatch.setattr(router, "_is_query_active", lambda session_id: False)
    monkeypatch.setattr(type(router.settings), "get_user", lambda self, user_id: {"id": user_id, "name": user_id, "role": "member", "enabled": True})
    monkeypatch.setattr(type(router.settings), "is_admin", lambda self, user_id: False)

    with pytest.raises(HTTPException) as exc_info:
        await router.commit_bug_pipeline_changes(
            "bug-1",
            GitCommitRequest(message="fix bug"),
            x_user_id="reviewer",
        )

    assert exc_info.value.status_code == 409
    assert "approved" in exc_info.value.detail


@pytest.mark.asyncio
async def test_bug_pipeline_artifact_endpoint_returns_allowed_process_output(monkeypatch, tmp_path):
    repo_path = tmp_path / "repo"
    artifact_dir = repo_path / ".ai" / "dev-fix" / "bug-1"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "fix_plan.md").write_text("# Fix Plan\n\nDo the change.", encoding="utf-8")
    fake_store = FakeBugPipelineStore()
    fake_store.create(
        {
            "pipeline_id": "bug-1",
            "user_id": "tester",
            "reviewer_id": "reviewer",
            "repo_key": "app",
            "repo_name": "app",
            "workspace_id": "ws-1",
            "session_id": "sess-1",
            "target_branch": "feature/sp11",
            "bugfix_branch": "bugfix/bug-1-fix",
            "namespace": "drama-dev",
            "affected_api": "GET /x",
            "problem_description": "bug",
            "expected_result": "ok",
            "actual_result": "fail",
            "artifact_dir": ".ai/dev-fix/bug-1",
        }
    )

    monkeypatch.setattr(router, "bug_pipeline_store", fake_store)
    monkeypatch.setattr(router, "resolve_session_repo_path", lambda session_id: repo_path)
    monkeypatch.setattr(type(router.settings), "get_user", lambda self, user_id: {"id": user_id, "name": user_id, "role": "member", "enabled": True})
    monkeypatch.setattr(type(router.settings), "is_admin", lambda self, user_id: False)

    response = await router.get_bug_pipeline_artifact("bug-1", "fix_plan.md", x_user_id="reviewer")

    assert response["content"].startswith("# Fix Plan")
    with pytest.raises(HTTPException) as exc_info:
        await router.get_bug_pipeline_artifact("bug-1", "../secret.txt", x_user_id="reviewer")
    assert exc_info.value.status_code == 404


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

    def fake_create_worktree(url, source_dir, worktree_path, branch=None, user_id=None, install_harness=True):
        calls.append((url, source_dir, worktree_path, branch, user_id, install_harness))
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
            True,
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
