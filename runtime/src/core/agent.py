"""
Agent session manager — wraps the Claude Agent SDK query().
"""

import logging
import os
from pathlib import Path
from typing import AsyncIterator, Optional

from claude_agent_sdk import (
    ProcessError,
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    SystemMessage,
    UserMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ThinkingBlock,
)

from src.config import settings
from src.core.session import session_store
from src.core.workspace import workspace_store
from src.harness.commands import normalize_command_prompt
from src.harness.loader import load_harness_config

logger = logging.getLogger(__name__)


def _apply_api_config() -> None:
    """Inject API auth and base URL into environment for the SDK to pick up."""
    if settings.anthropic_auth_token:
        os.environ["ANTHROPIC_AUTH_TOKEN"] = settings.anthropic_auth_token
    if settings.anthropic_base_url:
        os.environ["ANTHROPIC_BASE_URL"] = settings.anthropic_base_url


def _resolve_cwd(session_id: str) -> Path:
    """Return the working directory for a session.

    Sessions always run inside their bound git repo, not the runtime workspace wrapper.
    """
    return resolve_session_repo_path(session_id)


def resolve_session_repo_path(session_id: str) -> Path:
    """Resolve the git repo directory bound to a session."""
    rec = session_store.get(session_id)
    if not rec or not rec.get("workspace"):
        raise RuntimeError(f"Session has no bound workspace: {session_id}")
    workspace_id = rec.get("metadata", {}).get("workspace_id")
    repo_name = rec.get("metadata", {}).get("repo_name")
    workspace = workspace_store.get(workspace_id) if workspace_id else None
    if not workspace_id or not workspace:
        raise RuntimeError(f"Session is not bound to a valid workspace: {session_id}")
    if not repo_name:
        raise RuntimeError(f"Session is not bound to a git repo: {session_id}")

    for repo in workspace.get("repos", []):
        if repo.get("name") == repo_name:
            repo_path = Path(repo.get("local_path") or Path(workspace["cwd"]) / repo_name)
            if not repo_path.exists():
                raise RuntimeError(f"Session repo path does not exist: {repo_path}")
            return repo_path

    raise RuntimeError(f"Session repo not found in workspace: {repo_name}")


def _build_options(
    session_id: str,
    allowed_tools: Optional[list[str]] = None,
    max_turns: Optional[int] = None,
    max_budget_usd: Optional[float] = None,
    permission_mode: str = "acceptEdits",
) -> ClaudeAgentOptions:
    """
    Build ClaudeAgentOptions with fast-harness integration.

    Loads fast-harness plugin (commands, subagents, skills, hooks)
    so the agent can use: /implement, /fix, code-reviewer-agent, etc.
    """
    ws = _resolve_cwd(session_id)

    harness = load_harness_config()

    if allowed_tools is None:
        allowed_tools = [
            "Read", "Write", "Edit", "Bash", "Glob", "Grep",
            "WebSearch", "WebFetch", "Agent",
        ]

    return ClaudeAgentOptions(
        cwd=str(ws),
        allowed_tools=allowed_tools,
        permission_mode=permission_mode,
        resume=_get_sdk_session_id(session_id, ws),
        max_turns=max_turns or settings.default_max_turns,
        max_budget_usd=max_budget_usd or settings.default_max_budget_usd,
        setting_sources=["user", "project"],
        # Load fast-harness plugin — makes commands, agents, skills available
        plugins=harness.plugins,
        # Programmatic subagents from fast-harness agent definitions
        agents=harness.agents,
        # Enable all skills (both from harness plugin and any project-local ones)
        skills="all",
    )


def _get_sdk_session_id(session_id: str, cwd: Path) -> Optional[str]:
    rec = session_store.get(session_id)
    if not rec:
        return None
    metadata = rec.get("metadata", {})
    if metadata.get("sdk_session_cwd") != str(cwd):
        return None
    return metadata.get("sdk_session_id")


async def run_query_stream(
    session_id: str,
    prompt: str,
    allowed_tools: Optional[list[str]] = None,
    max_turns: Optional[int] = None,
    max_budget_usd: Optional[float] = None,
    permission_mode: str = "acceptEdits",
) -> AsyncIterator[dict]:
    """Run a query and yield structured messages suitable for SSE streaming."""
    options = _build_options(
        session_id=session_id,
        allowed_tools=allowed_tools,
        max_turns=max_turns,
        max_budget_usd=max_budget_usd,
        permission_mode=permission_mode,
    )

    session_store.touch(session_id)
    prompt = normalize_command_prompt(prompt)
    sdk_session_id: Optional[str] = None
    process_filter = StreamProcessFilter()
    _apply_api_config()

    try:
        async for message in _run_sdk_query(prompt, options):
            sdk_session_id = _extract_session_id(message, sdk_session_id)
            serialized = _serialize_message(message, process_filter)
            if serialized:
                yield serialized

    except Exception as exc:
        if options.resume and _is_missing_conversation_error(exc):
            logger.warning(
                "SDK session %s is missing for runtime session %s; starting a new SDK session",
                options.resume,
                session_id,
            )
            session_store.update_metadata(
                session_id,
                {"sdk_session_id": None, "sdk_session_cwd": None},
            )
            options.resume = None
            try:
                async for message in _run_sdk_query(prompt, options):
                    sdk_session_id = _extract_session_id(message, sdk_session_id)
                    serialized = _serialize_message(message, process_filter)
                    if serialized:
                        yield serialized
            except Exception as retry_exc:
                if _is_cancelled_process_error(retry_exc):
                    logger.info("Query cancelled for session %s: %s", session_id, retry_exc)
                    yield {"type": "cancelled", "message": "Request cancelled"}
                else:
                    logger.error("Query failed for session %s: %s", session_id, retry_exc)
                    yield {"type": "error", "message": str(retry_exc)}
        else:
            if _is_cancelled_process_error(exc):
                logger.info("Query cancelled for session %s: %s", session_id, exc)
                yield {"type": "cancelled", "message": "Request cancelled"}
            else:
                logger.error("Query failed for session %s: %s", session_id, exc)
                yield {"type": "error", "message": str(exc)}

    finally:
        if sdk_session_id:
            session_store.update_metadata(
                session_id,
                {
                    "sdk_session_id": sdk_session_id,
                    "sdk_session_cwd": str(options.cwd),
                },
            )


async def _run_sdk_query(prompt: str, options: ClaudeAgentOptions):
    async for message in query(prompt=prompt, options=options):
        yield message


def _is_missing_conversation_error(exc: Exception) -> bool:
    return "No conversation found with session ID" in str(exc)


def _is_cancelled_process_error(exc: Exception) -> bool:
    return isinstance(exc, ProcessError) and exc.exit_code == 143


class StreamProcessFilter:
    def __init__(self) -> None:
        self.hidden_tool_use_ids: set[str] = set()

    def should_show_tool(self, name: str) -> bool:
        visible_tools = _configured_tool_names()
        return "*" in visible_tools or name.lower() in visible_tools

    def hide_tool_use(self, tool_use_id: str) -> None:
        self.hidden_tool_use_ids.add(tool_use_id)

    def is_hidden_tool_result(self, tool_use_id: str) -> bool:
        return tool_use_id in self.hidden_tool_use_ids


def _configured_tool_names() -> set[str]:
    return {
        name.lower()
        for name in settings.stream_visible_tools
    }


def _should_show_thinking() -> bool:
    return settings.stream_show_thinking


def _extract_session_id(message, fallback: Optional[str]) -> Optional[str]:
    if isinstance(message, ResultMessage) and message.session_id:
        return message.session_id
    return fallback


def _serialize_message(
    message,
    process_filter: Optional[StreamProcessFilter] = None,
) -> Optional[dict]:
    """Convert SDK message types to JSON-serializable dicts."""
    process_filter = process_filter or StreamProcessFilter()

    # ── AssistantMessage: Claude's response with content blocks ──
    if isinstance(message, AssistantMessage):
        blocks = []
        for block in message.content:
            if isinstance(block, TextBlock):
                blocks.append({"type": "text", "text": block.text})
            elif isinstance(block, ToolUseBlock):
                if block.name == "AskUserQuestion":
                    blocks.append({
                        "type": "ask_user_question",
                        "id": block.id,
                        "questions": block.input.get("questions", []),
                    })
                else:
                    if not process_filter.should_show_tool(block.name):
                        process_filter.hide_tool_use(block.id)
                        continue
                    blocks.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
            elif isinstance(block, ThinkingBlock):
                if not _should_show_thinking():
                    continue
                blocks.append({
                    "type": "thinking",
                    "thinking": block.thinking,
                    "signature": getattr(block, "signature", None),
                })
            else:
                blocks.append({"type": "unknown", "data": str(block)})
        if not blocks:
            return None
        return {
            "type": "assistant",
            "content": blocks,
            "model": getattr(message, "model", None),
        }

    # ── UserMessage: tool results fed back to Claude ──
    if isinstance(message, UserMessage):
        blocks = []
        for block in message.content:
            if isinstance(block, ToolResultBlock):
                if process_filter.is_hidden_tool_result(block.tool_use_id):
                    continue
                blocks.append({
                    "type": "tool_result",
                    "tool_use_id": block.tool_use_id,
                    "content": block.content,
                    "is_error": block.is_error,
                })
            else:
                blocks.append({"type": "unknown", "data": str(block)})
        if not blocks:
            return None
        return {
            "type": "tool_results",
            "content": blocks,
            "parent_tool_use_id": getattr(message, "parent_tool_use_id", None),
        }

    # ── ResultMessage: final outcome ──
    if isinstance(message, ResultMessage):
        return {
            "type": "result",
            "subtype": message.subtype,
            "result": message.result,
            "session_id": message.session_id,
            "total_cost_usd": message.total_cost_usd,
            "usage": _serialize_usage(message),
        }

    # ── SystemMessage: init, compact_boundary, etc. ──
    if isinstance(message, SystemMessage):
        subtype = getattr(message, "subtype", "unknown")
        if subtype == "init":
            data = getattr(message, "data", {})
            return {
                "type": "system",
                "subtype": "init",
                "session_id": data.get("session_id", ""),
                "model": data.get("model", ""),
                "cwd": data.get("cwd", ""),
                "claude_code_version": data.get("claude_code_version", ""),
            }
        return {"type": "system", "subtype": subtype}

    return {"type": "unknown", "data": str(message)[:500]}


def _serialize_usage(message) -> Optional[dict]:
    try:
        return {
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
            "cache_creation_input_tokens": getattr(
                message.usage, "cache_creation_input_tokens", None
            ),
            "cache_read_input_tokens": getattr(
                message.usage, "cache_read_input_tokens", None
            ),
        }
    except Exception:
        return None
