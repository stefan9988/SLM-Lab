"""Agent initialization utilities."""

from typing import List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool

from config import settings
from logger import setup_logger

from .base import Agent

logger = setup_logger(__name__)


def _build_llm() -> BaseChatModel:
    """Build an LLM instance based on the configured provider."""
    provider = settings.LLM_PROVIDER.lower()
    logger.info("Building LLM (provider=%s, model=%s)", provider, settings.MODEL_NAME)

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=settings.MODEL_NAME, base_url=settings.OLLAMA_BASE_URL)
    elif provider == "openrouter":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.MODEL_NAME,
            openai_api_key=settings.OPEN_ROUTER_API_KEY,
            openai_api_base=settings.OPEN_ROUTER_BASE_URL,
            extra_body={"require": ["tools"]},
        )
    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER: {provider!r}. Use 'ollama' or 'openrouter'."
        )


def init_agent(
    system_prompt: Optional[str],
    tools: Optional[List[BaseTool]] = None,
    maintain_history: bool = False,
) -> Agent:
    """Initialize and return an Agent.

    Args:
        system_prompt: Optional system prompt. Defaults to GENERAL_AGENT_PROMPT.
        tools: Optional list of tools available to the agent.
        maintain_history: Whether to maintain conversation history across calls.

    Returns:
        Configured Agent instance.
    """
    tool_names = [t.name for t in tools] if tools else []
    logger.info(
        "init_agent called (tools=%s, maintain_history=%s)",
        tool_names,
        maintain_history,
    )
    try:
        llm = _build_llm()
        agent = Agent(
            llm=llm,
            system_prompt=system_prompt,
            tools=tools,
            maintain_history=maintain_history,
        )
        logger.info("init_agent successful")
        return agent
    except Exception:
        logger.error("init_agent failed", exc_info=True)
        raise
