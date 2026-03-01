"""Agent registry for cross-agent delegation.

Provides a module-level mapping of agent names to Agent instances,
populated during application startup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from AI.agents.base import Agent

_registry: dict[str, Agent] = {}
_allowed_callers: dict[str, set[str] | None] = {}


def register(name: str, agent: Agent, allowed_callers: set[str] | None = None) -> None:
    """Register an agent under *name*.

    Args:
        name: The name to register the agent under.
        agent: The agent instance.
        allowed_callers: A set of agent names that are allowed to call this
            agent via delegation.  ``None`` means unrestricted.
    """
    _registry[name] = agent
    _allowed_callers[name] = allowed_callers


def get(name: str) -> Agent | None:
    """Return the agent registered as *name*, or ``None``."""
    return _registry.get(name)


def get_allowed_callers(name: str) -> set[str] | None:
    """Return the allowed-callers set for *name*, or ``None`` if unrestricted."""
    return _allowed_callers.get(name)


def list_agents() -> list[str]:
    """Return the names of all registered agents."""
    return list(_registry.keys())


def clear() -> None:
    """Remove all registrations (useful in test teardown)."""
    _registry.clear()
    _allowed_callers.clear()
