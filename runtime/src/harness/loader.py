"""
Load fast-harness plugin configuration.

Reads the plugin/ directory to discover:
- Commands (plugin/commands/*.md)
- Agents (plugin/agents/*/xxx.md)
- Skills (plugin/skills/*/SKILL.md)

and produces the PluginConfig used by ClaudeAgentOptions.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from claude_agent_sdk import AgentDefinition

from src.config import settings
from src.harness.commands import command_display_name

logger = logging.getLogger(__name__)


@dataclass
class PluginConfig:
    plugins: list[dict] = field(default_factory=list)
    agents: dict[str, AgentDefinition] = field(default_factory=dict)
    commands: list[dict] = field(default_factory=list)
    skills: list[dict] = field(default_factory=list)
    mcp_servers: Path | None = None


def load_harness_config() -> PluginConfig:
    """Build PluginConfig from the fast-harness plugin directory."""
    plugin_path = settings.resolved_harness_path
    if not plugin_path.exists():
        logger.warning("Harness plugin path not found: %s", plugin_path)
        return PluginConfig()

    config = PluginConfig()

    # Load as a local SDK plugin (gives access to commands/, skills/, agents/, hooks/)
    config.plugins.append({"type": "local", "path": str(plugin_path)})
    mcp_config = plugin_path / ".mcp.json"
    if mcp_config.exists():
        config.mcp_servers = mcp_config

    # Discovery: parse agent definitions for programmatic registration
    _discover_agents(plugin_path, config)

    # Discovery: enumerate commands and skills for the /capabilities API
    _discover_commands(plugin_path, config)
    _discover_skills(plugin_path, config)

    return config


def _discover_agents(plugin_path: Path, config: PluginConfig) -> None:
    """Scan plugin/agents/ for subagent definitions."""
    agents_dir = plugin_path / "agents"
    if not agents_dir.is_dir():
        return

    for agent_dir in sorted(agents_dir.iterdir()):
        if not agent_dir.is_dir():
            continue
        md_files = list(agent_dir.glob("*.md"))
        if not md_files:
            continue

        agent_file = md_files[0]
        agent_name = agent_dir.name
        frontmatter, body = _parse_frontmatter(agent_file)

        if frontmatter:
            name = frontmatter.get("name", agent_name)
            description = frontmatter.get("description", f"Agent: {name}")
            tools = _parse_list(frontmatter.get("tools", ""))
            disallowed = _parse_list(frontmatter.get("disallowedTools", ""))
            mcp_servers = _parse_list(frontmatter.get("mcpServers", ""))
            model = frontmatter.get("model", "inherit")

            config.agents[name] = AgentDefinition(
                description=description,
                prompt=body,
                tools=tools if tools else None,
                disallowedTools=disallowed if disallowed else None,
                mcpServers=mcp_servers if mcp_servers else None,
                model=model if model != "inherit" else None,
            )

    logger.info("Discovered %d harness agents", len(config.agents))


def _discover_commands(plugin_path: Path, config: PluginConfig) -> None:
    """Scan plugin/commands/ for command definitions."""
    cmds_dir = plugin_path / "commands"
    if not cmds_dir.is_dir():
        return

    commands_by_name: dict[str, dict] = {}
    for cmd_file in sorted(cmds_dir.glob("*.md")):
        frontmatter, _body = _parse_frontmatter(cmd_file)
        invoke_name = cmd_file.stem
        display_name = command_display_name(invoke_name)
        command = {
            "name": display_name,
            "invoke": invoke_name,
            "description": (frontmatter.get("description", "") if frontmatter else ""),
            "path": str(cmd_file.relative_to(plugin_path)),
        }

        existing = commands_by_name.get(display_name)
        existing_is_legacy = bool(existing and existing["invoke"].endswith("-command"))
        new_is_legacy = invoke_name.endswith("-command")
        if existing is None or (existing_is_legacy and not new_is_legacy):
            commands_by_name[display_name] = command

    config.commands.extend(commands_by_name[name] for name in sorted(commands_by_name))

    logger.info("Discovered %d harness commands", len(config.commands))


def _discover_skills(plugin_path: Path, config: PluginConfig) -> None:
    """Scan plugin/skills/ for skill definitions."""
    skills_dir = plugin_path / "skills"
    if not skills_dir.is_dir():
        return

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            # Check for other .md files
            md_files = list(skill_dir.glob("*.md"))
            if md_files:
                skill_file = md_files[0]
            else:
                continue

        frontmatter, _body = _parse_frontmatter(skill_file)
        name = skill_dir.name
        config.skills.append({
            "name": name,
            "description": (frontmatter.get("description", "") if frontmatter else ""),
            "path": str(skill_file.relative_to(plugin_path)),
        })

    logger.info("Discovered %d harness skills", len(config.skills))


def _parse_frontmatter(filepath: Path) -> tuple[Optional[dict], str]:
    """Extract YAML frontmatter and body from a markdown file."""
    text = filepath.read_text()
    if not text.startswith("---"):
        return None, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, text

    try:
        import yaml
        meta = yaml.safe_load(parts[1])
    except Exception:
        # Minimal YAML parser for simple frontmatter (key: value)
        meta = {}
        for line in parts[1].strip().split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()

    return meta, parts[2].strip()


def _parse_list(value: str) -> list[str]:
    """Parse comma/semicolon separated string into a list."""
    if not value:
        return []
    # Handle both "Read, Edit, Bash" and YAML list format
    value = value.replace(";", ",")
    return [v.strip() for v in value.split(",") if v.strip()]
