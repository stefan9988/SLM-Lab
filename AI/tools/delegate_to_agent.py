"""Tool that lets one agent delegate a prompt to another registered agent."""

from __future__ import annotations

from uuid import uuid4

from langchain_core.runnables.config import var_child_runnable_config
from langchain_core.tools import tool
from langgraph.config import get_config, get_stream_writer

from AI.agents import registry
from BE.logger import setup_logger

logger = setup_logger(__name__)

# Tracks active delegations to prevent circular calls.
# Keyed by (user_id, agent_name).  Modified only from coroutines on the
# main event loop so no lock is required.
_active_delegations: set[tuple[str, str]] = set()


async def _run_delegation(
    agent_name: str, prompt: str, user_id: str, caller_name: str = ""
) -> str:
    """Execute the delegation inside the event loop with circular-call protection."""
    agent = registry.get(agent_name)
    if agent is None:
        return f"Error: Agent '{agent_name}' not found in registry."

    allowed = registry.get_allowed_callers(agent_name)
    if allowed is not None and caller_name not in allowed:
        return (
            f"Error: Agent '{agent_name}' can only be called by "
            f"{', '.join(sorted(allowed))}. Current caller: '{caller_name}'."
        )

    key = (user_id, agent_name)
    if key in _active_delegations:
        return (
            f"Error: Circular delegation detected — '{agent_name}' is already "
            f"handling a delegation for this user."
        )

    _active_delegations.add(key)
    # Reset the parent's runnable config so the delegated agent's tools
    # don't inherit the caller's stream writer.
    token = var_child_runnable_config.set(None)
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
        var_child_runnable_config.reset(token)
        _active_delegations.discard(key)


@tool
async def delegate_to_agent_tool(agent_name: str, prompt: str) -> str:
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
    writer(f"Asking {agent_name} for help…")

    # Validate agent exists
    if registry.get(agent_name) is None:
        available = registry.list_agents()
        logger.warning("Unknown agent '%s'. Available: %s", agent_name, available)
        return (
            f"Error: Unknown agent '{agent_name}'. "
            f"Available agents: {', '.join(available) if available else '(none)'}."
        )

    # Extract user_id and caller identity from config
    config = get_config()
    configurable = config.get("configurable", {})
    user_id: str = configurable.get("user_id", "")
    caller_name: str = configurable.get("agent_name", "")
    if not user_id:
        logger.warning("No user_id in config — cannot delegate")
        return "Error: Unable to determine user identity for delegation."

    result = await _run_delegation(agent_name, prompt, user_id, caller_name)

    logger.info(
        "delegate_to_agent_tool complete (target=%s, response_length=%d)",
        agent_name,
        len(result),
    )
    writer(f"Response received from {agent_name}")
    return result
