"""
Agent session manager — wraps the Claude Agent SDK query() and ClaudeSDKClient.
"""

import logging
import os
from pathlib import Path
from typing import AsyncIterator, Optional

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    ClaudeSDKClient,
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
from src.core.sandbox import get_session_workspace
from src.core.session import session_store
from src.harness.loader import load_harness_config

logger = logging.getLogger(__name__)


def _apply_api_config() -> None:
    """Inject API auth and base URL into environment for the SDK to pick up."""
    if settings.anthropic_auth_token:
        os.environ["ANTHROPIC_AUTH_TOKEN"] = settings.anthropic_auth_token
    if settings.anthropic_base_url:
        os.environ["ANTHROPIC_BASE_URL"] = settings.anthropic_base_url


def _resolve_cwd(session_id: str, workspace_id: Optional[str] = None) -> Path:
    """Return the working directory for a session.

    Priority: query-time workspace_id > session-bound workspace > session dir.
    """
    if workspace_id:
        from src.core.workspace import workspace_store
        ws_rec = workspace_store.get(workspace_id)
        if ws_rec:
            return Path(ws_rec["cwd"])
    rec = session_store.get(session_id)
    if rec and rec.get("workspace"):
        return Path(rec["workspace"])
    return get_session_workspace(session_id)


def _build_options(
    session_id: str,
    workspace_id: Optional[str] = None,
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
    ws = _resolve_cwd(session_id, workspace_id)

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


async def run_query_stream(
    session_id: str,
    prompt: str,
    workspace_id: Optional[str] = None,
    allowed_tools: Optional[list[str]] = None,
    max_turns: Optional[int] = None,
    max_budget_usd: Optional[float] = None,
    permission_mode: str = "acceptEdits",
) -> AsyncIterator[dict]:
    """
    Run a query and yield structured messages suitable for SSE streaming.

    If workspace_id is provided, the agent's cwd is set to that workspace
    (containing cloned git repos), and the session context is preserved.
    """
    options = _build_options(
        session_id=session_id,
        workspace_id=workspace_id,
        allowed_tools=allowed_tools,
        max_turns=max_turns,
        max_budget_usd=max_budget_usd,
        permission_mode=permission_mode,
    )

    session_store.touch(session_id)
    sdk_session_id: Optional[str] = None
    _apply_api_config()

    try:
        async for message in query(prompt=prompt, options=options):
            sdk_session_id = _extract_session_id(message, sdk_session_id)
            yield _serialize_message(message)

    except Exception as exc:
        logger.error("Query failed for session %s: %s", session_id, exc)
        yield {"type": "error", "message": str(exc)}

    finally:
        if sdk_session_id:
            session_store.update_metadata(session_id, {"sdk_session_id": sdk_session_id})


async def run_query_with_client(
    session_id: str,
    prompt: str,
    allowed_tools: Optional[list[str]] = None,
    max_turns: Optional[int] = None,
    max_budget_usd: Optional[float] = None,
) -> AsyncIterator[dict]:
    """
    Alternative: use ClaudeSDKClient for multi-turn conversation within a session.
    The client persists the session across multiple prompt() calls.
    """
    ws = _resolve_cwd(session_id)
    harness = load_harness_config()

    options = ClaudeAgentOptions(
        cwd=str(ws),
        allowed_tools=allowed_tools or [
            "Read", "Write", "Edit", "Bash", "Glob", "Grep",
            "WebSearch", "WebFetch", "Agent",
        ],
        permission_mode="acceptEdits",
        max_turns=max_turns or settings.default_max_turns,
        max_budget_usd=max_budget_usd or settings.default_max_budget_usd,
        setting_sources=["user", "project"],
        plugins=harness.plugins,
        agents=harness.agents,
        skills="all",
    )

    session_store.touch(session_id)
    _apply_api_config()

    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            async for message in client.receive_response():
                yield _serialize_message(message)
    except Exception as exc:
        logger.error("Query failed for session %s: %s", session_id, exc)
        yield {"type": "error", "message": str(exc)}


def _extract_session_id(message, fallback: Optional[str]) -> Optional[str]:
    if isinstance(message, ResultMessage) and message.session_id:
        return message.session_id
    return fallback


def _serialize_message(message) -> dict:
    """Convert SDK message types to JSON-serializable dicts."""

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
                    blocks.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
            elif isinstance(block, ThinkingBlock):
                blocks.append({
                    "type": "thinking",
                    "thinking": block.thinking,
                    "signature": getattr(block, "signature", None),
                })
            else:
                blocks.append({"type": "unknown", "data": str(block)})
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
                blocks.append({
                    "type": "tool_result",
                    "tool_use_id": block.tool_use_id,
                    "content": block.content,
                    "is_error": block.is_error,
                })
            else:
                blocks.append({"type": "unknown", "data": str(block)})
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
