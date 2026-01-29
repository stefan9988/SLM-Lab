"""Agent initialization utilities."""

from typing import List, Optional

from langchain_core.tools import BaseTool

from prompts import GENERAL_AGENT_PROMPT
from logger import setup_logger

from .base import OllamaAgent

logger = setup_logger(__name__)


def init_ollama_agent(
    system_prompt: Optional[str] = None,
    tools: Optional[List[BaseTool]] = None,
    maintain_history: bool = False,
) -> OllamaAgent:
    """Initialize and return an OllamaAgent.

    Args:
        system_prompt: Optional system prompt. Defaults to GENERAL_AGENT_PROMPT.
        tools: Optional list of tools available to the agent.
        maintain_history: Whether to maintain conversation history across calls.

    Returns:
        Configured OllamaAgent instance.
    """
    tool_names = [t.name for t in tools] if tools else []
    logger.info("init_ollama_agent called (tools=%s, maintain_history=%s)", tool_names, maintain_history)
    try:
        agent = OllamaAgent(
            system_prompt=system_prompt or GENERAL_AGENT_PROMPT,
            tools=tools,
            maintain_history=maintain_history,
        )
        logger.info("init_ollama_agent successful")
        return agent
    except Exception:
        logger.error("init_ollama_agent failed", exc_info=True)
        raise
