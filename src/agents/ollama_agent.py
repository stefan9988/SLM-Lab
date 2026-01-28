"""Ollama-based agent implementation."""

import logging
from typing import Iterator, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama

from config import settings

from .base import BaseAgent

logger = logging.getLogger(__name__)


class OllamaAgent(BaseAgent):
    """Agent implementation using Ollama as the LLM backend."""

    def __init__(
        self,
        model_name: str = settings.MODEL_NAME,
        base_url: str = settings.OLLAMA_BASE_URL,
        system_prompt: Optional[str] = None,
        tools: Optional[List[BaseTool]] = None,
        maintain_history: bool = False,
    ):
        """Initialize the Ollama agent.

        Args:
            model_name: The name of the Ollama model to use.
            base_url: The base URL of the Ollama server.
            system_prompt: Optional system prompt to prepend to conversations.
            tools: Optional list of tools available to the agent.
            maintain_history: Whether to maintain conversation history across calls.
        """
        self.model_name = model_name
        self.base_url = base_url
        super().__init__(
            system_prompt=system_prompt,
            tools=tools,
            maintain_history=maintain_history,
        )

    def _create_llm(self) -> BaseChatModel:
        """Create and return a ChatOllama instance.

        Returns:
            Configured ChatOllama instance.
        """
        return ChatOllama(model=self.model_name, base_url=self.base_url)

    def stream(self, prompt: str) -> Iterator[str]:
        """Stream response chunks for the given prompt.

        Implements an agentic loop that handles tool calls and continues
        streaming until a final response is generated.

        Args:
            prompt: The user's input prompt.

        Yields:
            String chunks of the response as they become available.
        """
        messages = self._build_messages(prompt)

        while True:
            collected_content = ""
            tool_calls = []

            for chunk in self._llm.stream(messages):
                if chunk.content:
                    collected_content += chunk.content
                    yield chunk.content
                if chunk.tool_calls:
                    tool_calls.extend(chunk.tool_calls)

            if not tool_calls:
                messages.append(AIMessage(content=collected_content))
                self._update_history(messages)
                break

            ai_message = AIMessage(content=collected_content, tool_calls=tool_calls)
            messages.append(ai_message)
            tool_messages = self._execute_tools(ai_message)
            messages.extend(tool_messages)

    def invoke(self, prompt: str) -> str:
        """Get a complete response for the given prompt.

        Implements an agentic loop that handles tool calls and continues
        invoking until a final response is generated.

        Args:
            prompt: The user's input prompt.

        Returns:
            The complete response string.
        """
        messages = self._build_messages(prompt)

        while True:
            response = self._llm.invoke(messages)
            if not response.tool_calls:
                messages.append(response)
                self._update_history(messages)
                return response.content

            messages.append(response)
            tool_messages = self._execute_tools(response)
            messages.extend(tool_messages)
