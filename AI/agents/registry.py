"""Agent registry for cross-agent delegation.

Provides a module-level mapping of agent names to Agent instances,
populated during application startup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from AI.agents.base import Agent

_registry: dict[str, Agent] = {}


def register(name: str, agent: Agent) -> None:
    """Register an agent under *name*."""
    _registry[name] = agent


def get(name: str) -> Agent | None:
    """Return the agent registered as *name*, or ``None``."""
    return _registry.get(name)


def list_agents() -> list[str]:
    """Return the names of all registered agents."""
    return list(_registry.keys())


def clear() -> None:
    """Remove all registrations (useful in test teardown)."""
    _registry.clear()
