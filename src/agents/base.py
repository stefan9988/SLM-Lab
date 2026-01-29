"""Abstract base class for agents."""

import logging
from abc import ABC, abstractmethod
from typing import Iterator, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class that defines the contract for agents.

    Subclasses must implement:
        - _create_llm(): Initialize and return the backend-specific LLM
        - stream(prompt): Stream response chunks
        - invoke(prompt): Get complete response

    Provides default implementations for:
        - clear_history(): Reset conversation
        - _build_messages(): Build message list
        - _update_history(): Update history
        - _execute_tools(): Execute tool calls
        - _bind_tools(): Bind tools to LLM
    """

    def __init__(
        self,
        system_prompt: Optional[str] = None,
        tools: Optional[List[BaseTool]] = None,
        maintain_history: bool = False,
    ):
        """Initialize the base agent.

        Args:
            system_prompt: Optional system prompt to prepend to conversations.
            tools: Optional list of tools available to the agent.
            maintain_history: Whether to maintain conversation history across calls.
        """
        self.system_prompt = system_prompt
        self.tools = tools or []
        self._tools_by_name = {tool.name: tool for tool in self.tools}
        self.maintain_history = maintain_history
        self._message_history: List = []
        self._llm = self._create_llm()
        self._bind_tools()

    @abstractmethod
    def _create_llm(self) -> BaseChatModel:
        """Create and return the backend-specific LLM instance.

        Returns:
            The initialized LLM instance.
        """
        pass

    @abstractmethod
    def stream(self, prompt: str) -> Iterator[str]:
        """Stream response chunks for the given prompt.

        Args:
            prompt: The user's input prompt.

        Yields:
            String chunks of the response as they become available.
        """
        pass

    @abstractmethod
    def invoke(self, prompt: str) -> str:
        """Get a complete response for the given prompt.

        Args:
            prompt: The user's input prompt.

        Returns:
            The complete response string.
        """
        pass

    def _bind_tools(self) -> None:
        """Bind tools to the LLM if tools are available."""
        if self.tools:
            self._llm = self._llm.bind_tools(self.tools)

    def _build_messages(self, prompt: str) -> List:
        """Build message list with optional system prompt.

        Args:
            prompt: The user's input prompt.

        Returns:
            List of messages including history, system prompt, and user message.
        """
        if self.maintain_history:
            messages = list(self._message_history)
        else:
            messages = []
        if self.system_prompt and not messages:
            messages.append(SystemMessage(content=self.system_prompt))
        messages.append(HumanMessage(content=prompt))
        return messages

    def _update_history(self, messages: List) -> None:
        """Update conversation history if history maintenance is enabled.

        Args:
            messages: The current list of messages to save as history.
        """
        if self.maintain_history:
            self._message_history = messages

    def _execute_tools(self, ai_message: AIMessage) -> List[ToolMessage]:
        """Execute tool calls and return tool messages.

        Args:
            ai_message: The AI message containing tool calls.

        Returns:
            List of ToolMessage objects with execution results.
        """
        tool_messages = []
        for tool_call in ai_message.tool_calls:
            tool_name = tool_call["name"]
            tool = self._tools_by_name.get(tool_name)
            if tool is None:
                logger.error(f"Unknown tool requested: {tool_name}")
                result = f"Error: Unknown tool '{tool_name}'"
            else:
                try:
                    logger.debug(f"Executing tool: {tool_name}")
                    result = tool.invoke(tool_call["args"])
                except Exception as e:
                    logger.error(f"Tool execution failed for {tool_name}: {e}")
                    result = f"Error executing {tool_name}: {e}"
            tool_messages.append(
                ToolMessage(content=str(result), tool_call_id=tool_call["id"])
            )
        return tool_messages

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self._message_history = []

    def get_history(self) -> List[dict]:
        """Get conversation history as serializable dicts.

        Returns:
            List of dictionaries with 'role' and 'content' keys.
        """
        return [
            {"role": msg.type, "content": msg.content}
            for msg in self._message_history
        ]
