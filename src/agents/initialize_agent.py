"""Agent initialization utilities."""

from typing import List, Optional

from langchain_core.tools import BaseTool

from prompts import SYSTEM_PROMPT

from .ollama_agent import OllamaAgent


def init_ollama_agent(
    system_prompt: Optional[str] = None,
    tools: Optional[List[BaseTool]] = None,
    maintain_history: bool = False,
) -> OllamaAgent:
    """Initialize and return an OllamaAgent.

    Args:
        system_prompt: Optional system prompt. Defaults to SYSTEM_PROMPT from prompts.
        tools: Optional list of tools available to the agent.
        maintain_history: Whether to maintain conversation history across calls.

    Returns:
        Configured OllamaAgent instance.
    """
    return OllamaAgent(
        system_prompt=system_prompt or SYSTEM_PROMPT,
        tools=tools,
        maintain_history=maintain_history,
    )
