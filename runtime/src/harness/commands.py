"""Helpers for user-facing slash command names.

The plugin keeps command files named ``*-command.md`` for historical reasons,
while the console UX advertises shorter names such as ``/implement``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping


LEGACY_COMMAND_SUFFIX = "-command"


def command_display_name(invoke_name: str) -> str:
    """Return the user-facing command name for a plugin command filename."""
    if invoke_name.endswith(LEGACY_COMMAND_SUFFIX):
        return invoke_name[: -len(LEGACY_COMMAND_SUFFIX)]
    return invoke_name


def normalize_command_prompt(
    prompt: str,
    commands: Iterable[Mapping[str, str]] | None = None,
) -> str:
    """Rewrite a user-facing slash command to the SDK command name.

    Example: ``/implement foo`` becomes ``/implement-command foo`` when the
    loaded plugin exposes ``{"name": "implement", "invoke": "implement-command"}``.
    Unknown commands and non-command prompts are returned unchanged.
    """
    match = re.match(r"^/([^\s/]+)(\s[\s\S]*)?$", prompt)
    if not match:
        return prompt

    entered_name = match.group(1)
    rest = match.group(2) or ""

    command_list = commands
    if command_list is None:
        from src.harness.loader import load_harness_config

        command_list = load_harness_config().commands

    invoke_by_name: dict[str, str] = {}
    for command in command_list:
        display_name = command.get("name", "")
        invoke_name = command.get("invoke", display_name)
        if display_name:
            invoke_by_name[display_name] = invoke_name
        if invoke_name:
            invoke_by_name[invoke_name] = invoke_name

    invoke_name = invoke_by_name.get(entered_name)
    if not invoke_name or invoke_name == entered_name:
        return prompt

    return f"/{invoke_name}{rest}"
