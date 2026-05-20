"""
Read-only registry of available harness capabilities.
Exposed via GET /api/capabilities.
"""

from src.harness.loader import load_harness_config


def get_capabilities() -> dict:
    config = load_harness_config()
    return {
        "commands": config.commands,
        "agents": {
            name: {
                "description": agent.description,
                "model": agent.model,
                "tools": agent.tools,
            }
            for name, agent in config.agents.items()
        },
        "skills": config.skills,
    }
