import logging
from typing import Iterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama

from config import settings
from tools.get_current_date_and_time import get_current_date_and_time

logger = logging.getLogger(__name__)


class Agent:
    """Agent class that wraps an LLM with streaming support."""

    def __init__(
        self,
        model_name: str = settings.MODEL_NAME,
        base_url: str = settings.OLLAMA_BASE_URL,
        system_prompt: str | None = None,
        tools: list[BaseTool] | None = None,
        maintain_history: bool = False,
    ):
        self.model_name = model_name
        self.base_url = base_url
        self.system_prompt = system_prompt
        self.tools = tools or [get_current_date_and_time]
        self._tools_by_name = {tool.name: tool for tool in self.tools}
        self._llm = ChatOllama(model=model_name, base_url=base_url)
        if self.tools:
            self._llm = self._llm.bind_tools(self.tools)
        self.maintain_history = maintain_history
        self._message_history: list = []

    def _build_messages(self, prompt: str) -> list:
        """Build message list with optional system prompt."""
        if self.maintain_history:
            messages = list(self._message_history)
        else:
            messages = []
        if self.system_prompt and not messages:
            messages.append(SystemMessage(content=self.system_prompt))
        messages.append(HumanMessage(content=prompt))
        return messages

    def _update_history(self, messages: list) -> None:
        """Update conversation history if history maintenance is enabled."""
        if self.maintain_history:
            self._message_history = messages

    def _execute_tools(self, ai_message: AIMessage) -> list[ToolMessage]:
        """Execute tool calls and return tool messages."""
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

    def stream(self, prompt: str) -> Iterator[str]:
        """Stream response chunks for the given prompt."""
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
        """Get a complete response for the given prompt."""
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

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self._message_history = []
