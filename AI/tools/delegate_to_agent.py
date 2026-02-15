"""Tool that lets one agent delegate a prompt to another registered agent."""

from __future__ import annotations

from uuid import uuid4

from langchain_core.tools import tool
from langgraph.config import get_config, get_stream_writer

from AI.agents import registry
from BE.async_utils import run_async_from_sync
from BE.logger import setup_logger

logger = setup_logger(__name__)

# Tracks active delegations to prevent circular calls.
# Keyed by (user_id, agent_name).  Modified only from coroutines on the
# main event loop so no lock is required.
_active_delegations: set[tuple[str, str]] = set()


async def _run_delegation(agent_name: str, prompt: str, user_id: str) -> str:
    """Execute the delegation inside the event loop with circular-call protection."""
    agent = registry.get(agent_name)
    if agent is None:
        return f"Error: Agent '{agent_name}' not found in registry."

    key = (user_id, agent_name)
    if key in _active_delegations:
        return (
            f"Error: Circular delegation detected — '{agent_name}' is already "
            f"handling a delegation for this user."
        )

    _active_delegations.add(key)
    try:
        session_id = f"delegate-{uuid4()}"
        response = await agent.invoke(
            prompt,
            session_id=session_id,
            user_id=user_id,
        )
        return response
    except Exception as exc:
        logger.error("Delegation to '%s' failed: %s", agent_name, exc, exc_info=True)
        return f"Error: Delegation to '{agent_name}' failed — {exc}"
    finally:
        _active_delegations.discard(key)


@tool
def delegate_to_agent_tool(agent_name: str, prompt: str) -> str:
    """Delegate a task to another agent by name.

    Use this tool when the current task would be better handled by a
    specialist agent.  Provide all relevant context in *prompt* — the
    target agent has no access to the current conversation history.

    Args:
        agent_name: Name of the target agent (e.g. "document_agent").
        prompt: Full prompt with all relevant context for the target agent.
    """
    logger.info(
        "delegate_to_agent_tool invoked (target=%s, prompt_length=%d)",
        agent_name,
        len(prompt),
    )
    writer = get_stream_writer()
    writer(f"Delegating to agent: {agent_name}")

    # Validate agent exists
    if registry.get(agent_name) is None:
        available = registry.list_agents()
        logger.warning("Unknown agent '%s'. Available: %s", agent_name, available)
        return (
            f"Error: Unknown agent '{agent_name}'. "
            f"Available agents: {', '.join(available) if available else '(none)'}."
        )

    # Extract user_id from config
    config = get_config()
    user_id: str = config.get("configurable", {}).get("user_id", "")
    if not user_id:
        logger.warning("No user_id in config — cannot delegate")
        return "Error: Unable to determine user identity for delegation."

    writer(f"Running delegation to {agent_name}…")
    result = run_async_from_sync(_run_delegation(agent_name, prompt, user_id))

    logger.info(
        "delegate_to_agent_tool complete (target=%s, response_length=%d)",
        agent_name,
        len(result),
    )
    writer("Delegation complete")
    return result
