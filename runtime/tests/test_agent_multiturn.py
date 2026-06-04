import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from claude_agent_sdk import (
    AssistantMessage,
    ProcessError,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from src.core import agent


def test_build_options_loads_plugin_mcp_config_and_allows_kube_tools(monkeypatch, tmp_path):
    mcp_config = tmp_path / ".mcp.json"
    mcp_config.write_text('{"mcpServers": {}}', encoding="utf-8")

    class FakeSessionStore:
        def get(self, session_id):
            return {"session_id": session_id, "metadata": {}}

    monkeypatch.setattr(agent, "session_store", FakeSessionStore())
    monkeypatch.setattr(agent, "_resolve_cwd", lambda session_id: Path(tmp_path))
    monkeypatch.setattr(
        agent,
        "load_harness_config",
        lambda: SimpleNamespace(plugins=[], agents={}, mcp_servers=mcp_config),
    )

    options = agent._build_options("runtime-session", allowed_tools=["Read"])

    assert options.mcp_servers == mcp_config
    assert "Read" in options.allowed_tools
    assert "mcp__kube-observability__diagnose_service" in options.allowed_tools
    assert "mcp__kube-observability__k8s_get_pod_logs" in options.allowed_tools


def test_build_user_content_includes_image_blocks_and_workspace_images(tmp_path):
    (tmp_path / "diagram.png").write_bytes(b"png")

    content = agent._build_user_content(
        "review this",
        [{"name": "paste.png", "mime_type": "image/png", "data": "aGVsbG8=", "size": 5}],
        SimpleNamespace(cwd=str(tmp_path)),
    )

    assert content[0]["type"] == "text"
    assert "review this" in content[0]["text"]
    assert "diagram.png" in content[0]["text"]
    assert content[1] == {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": "aGVsbG8=",
        },
    }


def test_build_user_content_lists_workspace_images_without_attachments(tmp_path):
    (tmp_path / "screens").mkdir()
    (tmp_path / "screens" / "shot.webp").write_bytes(b"webp")

    content = agent._build_user_content("use local images", [], SimpleNamespace(cwd=str(tmp_path)))

    assert isinstance(content, str)
    assert "screens/shot.webp" in content


@pytest.mark.asyncio
async def test_ask_user_question_answers_return_sdk_updated_input():
    session_id = "ask-session"
    agent._cleanup_answer_queue(session_id)
    output_queue = asyncio.Queue()

    task = asyncio.create_task(
        agent._answer_ask_user_question(
            session_id,
            {
                "questions": [
                    {
                        "question": "请选择运行模式。",
                        "options": [{"label": "完整模式"}, {"label": "快速模式"}],
                    }
                ]
            },
            output_queue=output_queue,
        )
    )

    event = await output_queue.get()
    assert event["type"] == "assistant"
    assert event["content"][0]["type"] == "ask_user_question"
    assert event["content"][0]["questions"] == [
        {
            "question": "请选择运行模式。",
            "options": [{"label": "完整模式"}, {"label": "快速模式"}],
        }
    ]

    await agent.provide_answers(
        session_id,
        [
            {
                "question": "请选择运行模式。",
                "answer": "完整模式",
                "tool_use_id": "toolu_ask",
            }
        ],
    )

    result = await task
    assert result.updated_input == {
        "questions": [
            {
                "question": "请选择运行模式。",
                "options": [{"label": "完整模式"}, {"label": "快速模式"}],
            }
        ],
        "answers": {"请选择运行模式。": "完整模式"},
    }
    agent._cleanup_answer_queue(session_id)


@pytest.mark.asyncio
async def test_generate_commit_message_uses_ai_subject(monkeypatch, tmp_path):
    captured = {}

    async def fake_query(*, prompt, options):
        captured["prompt"] = prompt
        captured["cwd"] = options.cwd
        yield AssistantMessage(
            content=[TextBlock(text='"Update runtime git actions"\n\nextra')],
            model="test-model",
        )

    monkeypatch.setattr(agent, "query", fake_query)

    message = await agent.generate_commit_message(tmp_path, "## status\n M runtime/ui/index.html")

    assert message == "Update runtime git actions"
    assert "runtime/ui/index.html" in captured["prompt"]
    assert captured["cwd"] == str(tmp_path)


@pytest.mark.asyncio
async def test_run_query_stream_resumes_previous_sdk_session(monkeypatch, tmp_path):
    captured_resumes = []

    class FakeSessionStore:
        def __init__(self):
            self.metadata = {
                "sdk_session_id": "sdk-prev",
                "sdk_session_cwd": str(tmp_path),
            }
            self.updated = None

        def get(self, session_id):
            return {"session_id": session_id, "metadata": dict(self.metadata)}

        def touch(self, session_id):
            pass

        def update_metadata(self, session_id, meta):
            self.updated = meta
            self.metadata.update(meta)

    async def fake_query(*, prompt, options):
        captured_resumes.append(options.resume)
        yield ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=1,
            session_id="sdk-next",
            result="ok",
        )

    monkeypatch.setattr(agent, "session_store", FakeSessionStore())
    monkeypatch.setattr(agent, "_resolve_cwd", lambda session_id: Path(tmp_path))
    monkeypatch.setattr(agent, "query", fake_query)

    messages = [
        message async for message in agent.run_query_stream("runtime-session", "继续上文")
    ]

    assert captured_resumes == ["sdk-prev"]
    assert messages[-1]["session_id"] == "sdk-next"
    assert agent.session_store.updated == {
        "sdk_session_id": "sdk-next",
        "sdk_session_cwd": str(tmp_path),
    }


@pytest.mark.asyncio
async def test_run_query_stream_starts_new_sdk_session_without_previous_id(monkeypatch, tmp_path):
    captured_resumes = []

    class FakeSessionStore:
        def get(self, session_id):
            return {"session_id": session_id, "metadata": {}}

        def touch(self, session_id):
            pass

        def update_metadata(self, session_id, meta):
            pass

    async def fake_query(*, prompt, options):
        captured_resumes.append(options.resume)
        yield ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=1,
            session_id="sdk-first",
            result="ok",
        )

    monkeypatch.setattr(agent, "session_store", FakeSessionStore())
    monkeypatch.setattr(agent, "_resolve_cwd", lambda session_id: Path(tmp_path))
    monkeypatch.setattr(agent, "query", fake_query)

    _messages = [
        message async for message in agent.run_query_stream("runtime-session", "第一轮")
    ]

    assert captured_resumes == [None]


@pytest.mark.asyncio
async def test_run_query_stream_ignores_sdk_session_from_different_cwd(monkeypatch, tmp_path):
    captured_resumes = []

    class FakeSessionStore:
        def get(self, session_id):
            return {
                "session_id": session_id,
                "metadata": {
                    "sdk_session_id": "sdk-old",
                    "sdk_session_cwd": str(tmp_path / "old-wrapper"),
                },
            }

        def touch(self, session_id):
            pass

        def update_metadata(self, session_id, meta):
            pass

    async def fake_query(*, prompt, options):
        captured_resumes.append(options.resume)
        yield ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=1,
            session_id="sdk-new",
            result="ok",
        )

    monkeypatch.setattr(agent, "session_store", FakeSessionStore())
    monkeypatch.setattr(agent, "_resolve_cwd", lambda session_id: Path(tmp_path))
    monkeypatch.setattr(agent, "query", fake_query)

    _messages = [
        message async for message in agent.run_query_stream("runtime-session", "新的 cwd")
    ]

    assert captured_resumes == [None]


@pytest.mark.asyncio
async def test_run_query_stream_retries_without_stale_resume(monkeypatch, tmp_path):
    captured_resumes = []

    class FakeSessionStore:
        def __init__(self):
            self.metadata = {
                "sdk_session_id": "sdk-missing",
                "sdk_session_cwd": str(tmp_path),
            }
            self.updates = []

        def get(self, session_id):
            return {"session_id": session_id, "metadata": dict(self.metadata)}

        def touch(self, session_id):
            pass

        def update_metadata(self, session_id, meta):
            self.updates.append(meta)
            self.metadata.update(meta)

    async def fake_query(*, prompt, options):
        captured_resumes.append(options.resume)
        if options.resume == "sdk-missing":
            raise RuntimeError("No conversation found with session ID: sdk-missing")
        yield ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=1,
            session_id="sdk-recovered",
            result="ok",
        )

    fake_store = FakeSessionStore()
    monkeypatch.setattr(agent, "session_store", fake_store)
    monkeypatch.setattr(agent, "_resolve_cwd", lambda session_id: Path(tmp_path))
    monkeypatch.setattr(agent, "query", fake_query)

    messages = [
        message async for message in agent.run_query_stream("runtime-session", "恢复")
    ]

    assert captured_resumes == ["sdk-missing", None]
    assert messages[-1]["session_id"] == "sdk-recovered"
    assert fake_store.updates[-1] == {
        "sdk_session_id": "sdk-recovered",
        "sdk_session_cwd": str(tmp_path),
    }


@pytest.mark.asyncio
async def test_run_query_stream_treats_exit_143_as_cancelled(monkeypatch, tmp_path):
    class FakeSessionStore:
        def get(self, session_id):
            return {"session_id": session_id, "metadata": {}}

        def touch(self, session_id):
            pass

        def update_metadata(self, session_id, meta):
            raise AssertionError("cancelled runs must not update sdk session metadata")

    async def fake_query(*, prompt, options):
        raise ProcessError("Command failed with exit code 143", exit_code=143)
        yield

    monkeypatch.setattr(agent, "session_store", FakeSessionStore())
    monkeypatch.setattr(agent, "_resolve_cwd", lambda session_id: Path(tmp_path))
    monkeypatch.setattr(agent, "query", fake_query)

    messages = [
        message async for message in agent.run_query_stream("runtime-session", "取消")
    ]

    assert messages == [{"type": "cancelled", "message": "Request cancelled"}]


def test_stream_filter_hides_tool_calls_and_results_by_default(monkeypatch):
    monkeypatch.setattr(agent, "_configured_tool_names", lambda: set())
    process_filter = agent.StreamProcessFilter()

    tool_message = AssistantMessage(
        content=[ToolUseBlock(id="toolu_1", name="Bash", input={"command": "pwd"})],
        model="test-model",
    )
    result_message = UserMessage(
        content=[ToolResultBlock(tool_use_id="toolu_1", content="out", is_error=False)]
    )

    assert agent._serialize_message(tool_message, process_filter) is None
    assert agent._serialize_message(result_message, process_filter) is None


def test_stream_filter_can_show_configured_tools(monkeypatch):
    monkeypatch.setattr(agent, "_configured_tool_names", lambda: {"bash"})
    process_filter = agent.StreamProcessFilter()

    tool_message = AssistantMessage(
        content=[ToolUseBlock(id="toolu_1", name="Bash", input={"command": "pwd"})],
        model="test-model",
    )
    result_message = UserMessage(
        content=[ToolResultBlock(tool_use_id="toolu_1", content="out", is_error=False)]
    )

    assert agent._serialize_message(tool_message, process_filter) == {
        "type": "assistant",
        "content": [
            {
                "type": "tool_use",
                "id": "toolu_1",
                "name": "Bash",
                "input": {"command": "pwd"},
            }
        ],
        "model": "test-model",
    }
    assert agent._serialize_message(result_message, process_filter) == {
        "type": "tool_results",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "toolu_1",
                "content": "out",
                "is_error": False,
            }
        ],
        "parent_tool_use_id": None,
    }
