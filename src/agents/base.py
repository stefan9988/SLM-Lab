"""LangGraph-based reactive agent wrapper."""

import logging
from typing import Iterator, List, Optional

from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from config import settings

logger = logging.getLogger(__name__)


class OllamaAgent:
    """Agent using LangChain's create_agent with an Ollama backend."""

    def __init__(
        self,
        model_name: str = settings.MODEL_NAME,
        base_url: str = settings.OLLAMA_BASE_URL,
        system_prompt: Optional[str] = None,
        tools: Optional[List[BaseTool]] = None,
        maintain_history: bool = False,
    ):
        self.maintain_history = maintain_history
        self._message_history: List = []

        llm = ChatOllama(model=model_name, base_url=base_url)
        self._agent = create_agent(
            model=llm,
            tools=tools or [],
            system_prompt=system_prompt,
        )

    def invoke(self, prompt: str) -> str:
        """Get a complete response for the given prompt."""
        messages = self._get_input_messages(prompt)
        result = self._agent.invoke({"messages": messages})
        all_messages = result["messages"]
        self._save_history(all_messages)
        return all_messages[-1].content

    
    def stream(self, prompt: str):
        messages = self._get_input_messages(prompt)

        full_response = []
        for stream_mode, chunk in self._agent.stream(
            {"messages": messages}, stream_mode=["messages", "custom"]
        ):
            if stream_mode == "custom":
                yield {"type": "status", "content": chunk}
            elif stream_mode == "messages":
                msg_chunk, metadata = chunk
                if isinstance(msg_chunk, AIMessageChunk):
                    if msg_chunk.tool_call_chunks:
                        for tc in msg_chunk.tool_call_chunks:
                            if tc.get("name"):
                                yield {"type": "status", "content": f"Calling tool: {tc['name']}"}
                    elif msg_chunk.content:
                        full_response.append(msg_chunk.content)
                        yield {"type": "token", "content": msg_chunk.content}
                elif isinstance(msg_chunk, ToolMessage):
                    yield {"type": "status", "content": "Tool returned result"}

        all_messages = list(messages) + [AIMessage(content="".join(full_response))]
        self._save_history(all_messages)


    def clear_history(self) -> None:
        """Clear the conversation history."""
        self._message_history = []

    def get_history(self) -> List[dict]:
        """Get conversation history as serializable dicts."""
        return [
            {"role": msg.type, "content": msg.content}
            for msg in self._message_history
        ]

    def _get_input_messages(self, prompt: str) -> List:
        if self.maintain_history:
            return list(self._message_history) + [HumanMessage(content=prompt)]
        return [HumanMessage(content=prompt)]

    def _save_history(self, messages: List) -> None:
        if self.maintain_history:
            self._message_history = messages
