"""
Agent session manager — wraps the Claude Agent SDK query().
"""

import asyncio
import logging
import os
import re
import uuid
from contextlib import suppress
from pathlib import Path
from typing import Any, AsyncIterator, Optional

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
from claude_agent_sdk.types import HookMatcher, PermissionResultAllow

from src.config import settings
from src.core.session import session_store
from src.core.workspace import workspace_store
from src.harness.commands import normalize_command_prompt
from src.harness.loader import load_harness_config

logger = logging.getLogger(__name__)


KUBE_OBSERVABILITY_ALLOWED_TOOLS = [
    "mcp__kube-observability__k8s_list_pods",
    "mcp__kube-observability__k8s_get_pod_detail",
    "mcp__kube-observability__k8s_list_deployments",
    "mcp__kube-observability__k8s_get_events",
    "mcp__kube-observability__k8s_get_pod_logs",
    "mcp__kube-observability__loki_search_logs",
    "mcp__kube-observability__loki_query_range",
    "mcp__kube-observability__prometheus_query_range",
    "mcp__kube-observability__prometheus_service_http_overview",
    "mcp__kube-observability__prometheus_pod_resources",
    "mcp__kube-observability__diagnose_service",
]

IMAGE_FILE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MAX_DISCOVERED_IMAGE_FILES = 50
MAX_COMMIT_MESSAGE_LENGTH = 72

# @-mention file references in a prompt, e.g. "@src/app.py".
# A path runs until whitespace; it may contain dots, dashes, slashes, underscores.
MENTION_PATTERN = re.compile(r"(?<!\S)@([^\s@]+)")
MAX_MENTION_FILES = 10
MAX_MENTION_FILE_BYTES = 100_000
MAX_MENTION_TOTAL_BYTES = 300_000


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
    metadata = rec.get("metadata", {})
    session_repo_path = metadata.get("session_repo_path")
    if session_repo_path:
        repo_path = Path(session_repo_path)
        if not repo_path.exists():
            raise RuntimeError(f"Session repo path does not exist: {repo_path}")
        return repo_path

    workspace_id = metadata.get("workspace_id")
    repo_name = metadata.get("repo_name")
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
    allowed_tools = _with_kube_observability_tools(allowed_tools)

    return ClaudeAgentOptions(
        cwd=str(ws),
        allowed_tools=allowed_tools,
        mcp_servers=harness.mcp_servers or {},
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


def _with_kube_observability_tools(allowed_tools: list[str]) -> list[str]:
    merged = list(allowed_tools)
    seen = set(merged)
    for tool_name in KUBE_OBSERVABILITY_ALLOWED_TOOLS:
        if tool_name not in seen:
            merged.append(tool_name)
            seen.add(tool_name)
    return merged


def _get_sdk_session_id(session_id: str, cwd: Path) -> Optional[str]:
    rec = session_store.get(session_id)
    if not rec:
        return None
    metadata = rec.get("metadata", {})
    if metadata.get("sdk_session_cwd") != str(cwd):
        return None
    return metadata.get("sdk_session_id")


# Per-session queues for feeding AskUserQuestion answers back to the SDK callback.
_answer_queues: dict[str, asyncio.Queue] = {}


def _get_answer_queue(session_id: str) -> asyncio.Queue:
    if session_id not in _answer_queues:
        _answer_queues[session_id] = asyncio.Queue()
    return _answer_queues[session_id]


def _cleanup_answer_queue(session_id: str) -> None:
    _answer_queues.pop(session_id, None)


async def provide_answers(session_id: str, answers: list[dict]) -> None:
    """Push AskUserQuestion answers into the running SDK stream."""
    queue = _answer_queues.get(session_id)
    if not queue:
        raise RuntimeError("No active query for this session")
    await queue.put(answers)


async def generate_commit_message(repo_path: Path, change_context: str) -> str:
    """Use the configured AI model to produce a concise commit subject."""
    if not change_context.strip():
        return "Update code"

    _apply_api_config()
    prompt = (
        "Write one concise Git commit subject for the following repository changes.\n"
        "Return only the commit subject, no quotes, no markdown, no explanation.\n"
        "Keep it under 72 characters. Prefer an imperative verb.\n\n"
        f"{change_context}"
    )
    options = ClaudeAgentOptions(
        cwd=str(repo_path),
        allowed_tools=[],
        permission_mode="acceptEdits",
        max_turns=1,
        max_budget_usd=min(settings.default_max_budget_usd, 0.25),
        setting_sources=["user", "project"],
    )

    chunks: list[str] = []
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    chunks.append(block.text)
        elif isinstance(message, ResultMessage):
            result = getattr(message, "result", "")
            if result:
                chunks.append(str(result))

    subject = _clean_commit_subject("\n".join(chunks))
    if not subject:
        raise RuntimeError("AI did not return a commit message")
    return subject


def _clean_commit_subject(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    subject = lines[0].strip("`'\" ")
    for prefix in ("Commit message:", "commit message:"):
        if subject.startswith(prefix):
            subject = subject[len(prefix):].strip()
    if len(subject) > MAX_COMMIT_MESSAGE_LENGTH:
        subject = subject[:MAX_COMMIT_MESSAGE_LENGTH].rstrip(" .,:;")
    return subject


async def run_query_stream(
    session_id: str,
    prompt: str,
    images: Optional[list[dict[str, Any]]] = None,
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
        async for message in _run_sdk_query(prompt, options, session_id, images=images):
            sdk_session_id = _extract_session_id(message, sdk_session_id)
            serialized = (
                message
                if isinstance(message, dict)
                else _serialize_message(message, process_filter)
            )
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
                async for message in _run_sdk_query(prompt, options, session_id, images=images):
                    sdk_session_id = _extract_session_id(message, sdk_session_id)
                    serialized = (
                        message
                        if isinstance(message, dict)
                        else _serialize_message(message, process_filter)
                    )
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
        _cleanup_answer_queue(session_id)
        if sdk_session_id:
            session_store.update_metadata(
                session_id,
                {
                    "sdk_session_id": sdk_session_id,
                    "sdk_session_cwd": str(options.cwd),
                },
            )


async def _run_sdk_query(
    prompt: str,
    options: ClaudeAgentOptions,
    session_id: str = "",
    images: Optional[list[dict[str, Any]]] = None,
):
    """Run SDK query in streaming mode so answers can be fed back via the queue."""
    _get_answer_queue(session_id)
    output_queue: asyncio.Queue = asyncio.Queue()
    options.can_use_tool = _build_can_use_tool(session_id, output_queue)
    options.hooks = _merge_pre_tool_use_hook(getattr(options, "hooks", None))

    async def _prompt_stream():
        yield {
            "type": "user",
            "session_id": "",
            "message": {"role": "user", "content": _build_user_content(prompt, images, options)},
            "parent_tool_use_id": None,
        }

    done = object()

    async def _produce_messages():
        try:
            async for message in query(prompt=_prompt_stream(), options=options):
                await output_queue.put(message)
        except Exception as exc:
            await output_queue.put(exc)
        finally:
            await output_queue.put(done)

    task = asyncio.create_task(_produce_messages())
    try:
        while True:
            item = await output_queue.get()
            if item is done:
                break
            if isinstance(item, Exception):
                raise item
            yield item
    finally:
        if not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


def _build_user_content(
    prompt: str,
    images: Optional[list[dict[str, Any]]],
    options: ClaudeAgentOptions,
) -> str | list[dict[str, Any]]:
    image_blocks = [_image_attachment_to_content_block(image) for image in images or []]
    text = _build_user_text(prompt, image_blocks, options)
    if not image_blocks:
        return text
    return [{"type": "text", "text": text}, *image_blocks]


def _image_attachment_to_content_block(image: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": image["mime_type"],
            "data": image["data"],
        },
    }


def _build_user_text(
    prompt: str,
    image_blocks: list[dict[str, Any]],
    options: ClaudeAgentOptions,
) -> str:
    parts = [prompt]
    if image_blocks:
        parts.append(
            f"\n\n[fast-harness attached {len(image_blocks)} image(s) to this message. "
            "Use the visual content directly when answering.]"
        )

    discovered_images = _discover_workspace_images(Path(str(options.cwd)))
    if discovered_images:
        listing = "\n".join(f"- {path}" for path in discovered_images)
        parts.append(
            "\n\n[fast-harness detected image files in the current repository. "
            "When the task refers to local screenshots, diagrams, or other images, "
            "use the Read tool on the relevant path without asking the user to paste it again.]\n"
            f"{listing}"
        )

    mention_context = _build_mention_context(prompt, Path(str(options.cwd)))
    if mention_context:
        parts.append(mention_context)
    return "".join(parts)


def _build_mention_context(prompt: str, cwd: Path) -> str:
    """Read files referenced via @path in the prompt and return them as a context block.

    Paths are resolved relative to the workspace root (`cwd`). References that escape
    the workspace, point at missing files, or are not regular files are skipped.
    Content is bounded per-file and in total to keep the prompt size reasonable.
    """
    mentions = _extract_mentions(prompt)
    if not mentions:
        return ""

    if not cwd.exists():
        return ""
    cwd_resolved = cwd.resolve()

    blocks: list[str] = []
    seen: set[str] = set()
    total_bytes = 0
    for rel_path in mentions:
        if rel_path in seen:
            continue
        seen.add(rel_path)
        if len(blocks) >= MAX_MENTION_FILES:
            break

        target = (cwd_resolved / rel_path).resolve()
        # Guard against path traversal outside the workspace.
        if cwd_resolved != target and cwd_resolved not in target.parents:
            continue
        if not target.is_file():
            continue

        try:
            data = target.read_bytes()
        except OSError:
            continue

        truncated = False
        if len(data) > MAX_MENTION_FILE_BYTES:
            data = data[:MAX_MENTION_FILE_BYTES]
            truncated = True
        if total_bytes + len(data) > MAX_MENTION_TOTAL_BYTES:
            break
        total_bytes += len(data)

        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            # Skip binary files — they aren't useful as text context.
            continue

        suffix = "\n\n[... 内容超长，已截断 ...]" if truncated else ""
        blocks.append(f"### {rel_path}\n```\n{text}\n```{suffix}")

    if not blocks:
        return ""

    body = "\n\n".join(blocks)
    return (
        "\n\n[fast-harness 已根据用户输入中的 @ 引用，附上以下工作区文件的内容作为上下文。"
        "请直接使用这些内容，无需再次调用工具读取（除非需要查看截断或未引用的部分）。]\n\n"
        f"{body}"
    )


def _extract_mentions(prompt: str) -> list[str]:
    """Return the ordered list of @-referenced paths in a prompt."""
    mentions: list[str] = []
    for match in MENTION_PATTERN.finditer(prompt):
        raw = match.group(1)
        # Trim trailing punctuation that commonly abuts a path in prose.
        raw = raw.rstrip(".,;:)]}'\"")
        if raw:
            mentions.append(raw)
    return mentions


def _discover_workspace_images(cwd: Path) -> list[str]:
    if not cwd.exists():
        return []
    images: list[str] = []
    skipped_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__"}
    try:
        for path in cwd.rglob("*"):
            if len(images) >= MAX_DISCOVERED_IMAGE_FILES:
                break
            if any(part in skipped_dirs for part in path.parts):
                continue
            if path.is_file() and path.suffix.lower() in IMAGE_FILE_EXTENSIONS:
                images.append(str(path.relative_to(cwd)))
    except OSError:
        return images
    return sorted(images)


def _build_can_use_tool(session_id: str, output_queue: asyncio.Queue | None = None):
    async def can_use_tool(tool_name: str, input_data: dict, context):
        if tool_name == "AskUserQuestion":
            return await _answer_ask_user_question(
                session_id,
                input_data,
                context=context,
                output_queue=output_queue,
            )
        return PermissionResultAllow(updated_input=input_data)

    return can_use_tool


async def _answer_ask_user_question(
    session_id: str,
    input_data: dict,
    context=None,
    output_queue: asyncio.Queue | None = None,
) -> PermissionResultAllow:
    """Wait for the web UI to answer AskUserQuestion and return SDK-shaped input."""
    queue = _get_answer_queue(session_id)
    questions = input_data.get("questions", [])
    if output_queue is not None:
        await output_queue.put(_build_ask_user_question_event(input_data, context))

    while True:
        answer_batch = await queue.get()
        try:
            answers = _build_answers_map(answer_batch)
            if _answers_cover_questions(questions, answers):
                return PermissionResultAllow(
                    updated_input={
                        "questions": questions,
                        "answers": answers,
                    },
                )
            logger.warning(
                "Ignoring incomplete AskUserQuestion answer batch for session %s: %s",
                session_id,
                list(answers),
            )
        finally:
            queue.task_done()


def _build_answers_map(answer_batch: list[dict]) -> dict:
    """Map API answer entries to the object expected by AskUserQuestion."""
    answers: dict = {}
    for item in answer_batch:
        question = item.get("question")
        if not question:
            continue
        answers[question] = item.get("answer")
    return answers


def _answers_cover_questions(questions: list[dict], answers: dict) -> bool:
    for question in questions:
        q_text = question.get("question") or question.get("header") or ""
        answer = answers.get(q_text)
        if isinstance(answer, list):
            if not answer:
                return False
        elif not answer:
            return False
    return True


def _build_ask_user_question_event(input_data: dict, context=None) -> dict:
    tool_use_id = (
        getattr(context, "tool_use_id", None)
        or getattr(context, "toolUseID", None)
        or f"ask_{uuid.uuid4().hex}"
    )
    return {
        "type": "assistant",
        "content": [
            {
                "type": "ask_user_question",
                "id": tool_use_id,
                "questions": input_data.get("questions", []),
            }
        ],
        "model": None,
    }


async def _keep_stream_open_hook(input_data, tool_use_id, context):
    return {"continue_": True}


def _merge_pre_tool_use_hook(hooks):
    merged = dict(hooks or {})
    pre_tool_hooks = list(merged.get("PreToolUse", []))
    pre_tool_hooks.append(HookMatcher(matcher=None, hooks=[_keep_stream_open_hook]))
    merged["PreToolUse"] = pre_tool_hooks
    return merged


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
                    continue
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
