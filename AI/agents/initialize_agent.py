"""Agent initialization utilities."""

from typing import List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool

from BE.config import settings
from BE.logger import setup_logger
from BE.session_store import SessionStore, create_store

from .base import Agent

logger = setup_logger(__name__)


def _build_llm(provider: str, model_name: str) -> BaseChatModel:
    """Build an LLM instance for the given provider and model."""
    logger.info("Building LLM (provider=%s, model=%s)", provider, model_name)

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        kwargs = {"model": model_name, "base_url": settings.OLLAMA_BASE_URL}
        if settings.OLLAMA_THINKING:
            kwargs["reasoning"] = True
        return ChatOllama(**kwargs)
    elif provider == "openrouter":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model_name,
            openai_api_key=settings.OPEN_ROUTER_API_KEY,
            openai_api_base=settings.OPEN_ROUTER_BASE_URL,
            extra_body={"require": ["tools"]},
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=model_name,
            api_key=settings.ANTHROPIC_API_KEY,
        )
    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER: {provider!r}. "
            "Use 'ollama', 'openrouter', or 'anthropic'."
        )


def init_agent(
    system_prompt: Optional[str],
    tools: Optional[List[BaseTool]] = None,
    maintain_history: bool = False,
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    agent_name: str = "",
    session_store: Optional[SessionStore] = None,
) -> Agent:
    """Initialize and return an Agent.

    Args:
        system_prompt: Optional system prompt. Defaults to GENERAL_AGENT_PROMPT.
        tools: Optional list of tools available to the agent.
        maintain_history: Whether to maintain conversation history across calls.
        provider: LLM provider override. Falls back to global LLM_PROVIDER.
        model_name: Model name override. Falls back to global MODEL_NAME.
        session_store: Optional pre-built session store. Defaults to create_store().

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
        resolved_provider = (provider or settings.LLM_PROVIDER).lower()
        resolved_model = model_name or settings.MODEL_NAME
        llm = _build_llm(resolved_provider, resolved_model)
        store = session_store if session_store is not None else create_store()
        agent = Agent(
            llm=llm,
            system_prompt=system_prompt,
            tools=tools,
            maintain_history=maintain_history,
            session_store=store,
            model_name=resolved_model,
            provider=resolved_provider,
            agent_name=agent_name,
        )
        logger.info("init_agent successful")
        return agent
    except Exception:
        logger.error("init_agent failed", exc_info=True)
        raise
