"""LangGraph-based reactive agent wrapper."""

from typing import Iterator, List, Optional

from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from config import settings
from logger import setup_logger

logger = setup_logger(__name__)


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

        tool_names = [t.name for t in tools] if tools else []
        logger.info("Initializing OllamaAgent (model=%s, tools=%s)", model_name, tool_names)

        try:
            llm = ChatOllama(model=model_name, base_url=base_url)
            self._agent = create_agent(
                model=llm,
                tools=tools or [],
                system_prompt=system_prompt,
            )
            logger.info("OllamaAgent initialized successfully")
        except Exception:
            logger.error("Failed to initialize OllamaAgent", exc_info=True)
            raise

    def invoke(self, prompt: str) -> str:
        """Get a complete response for the given prompt."""
        logger.info("invoke called (prompt_length=%d)", len(prompt))
        logger.debug("invoke prompt: %s", prompt)
        try:
            messages = self._get_input_messages(prompt)
            result = self._agent.invoke({"messages": messages})
            all_messages = result["messages"]
            self._save_history(all_messages)
            response = all_messages[-1].content
            logger.info("invoke complete (response_length=%d)", len(response))
            return response
        except Exception:
            logger.error("invoke failed", exc_info=True)
            raise


    def stream(self, prompt: str):
        logger.info("stream called (prompt_length=%d)", len(prompt))
        logger.debug("stream prompt: %s", prompt)
        try:
            messages = self._get_input_messages(prompt)

            full_response = []
            token_count = 0
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
                                    logger.info("Tool call: %s", tc["name"])
                                    yield {"type": "status", "content": f"Calling tool: {tc['name']}"}
                        elif msg_chunk.content:
                            full_response.append(msg_chunk.content)
                            token_count += 1
                            yield {"type": "token", "content": msg_chunk.content}
                    elif isinstance(msg_chunk, ToolMessage):
                        yield {"type": "status", "content": "Tool returned result"}

            all_messages = list(messages) + [AIMessage(content="".join(full_response))]
            self._save_history(all_messages)
            logger.info("stream complete (tokens=%d)", token_count)
        except Exception:
            logger.error("stream failed", exc_info=True)
            raise


    def clear_history(self) -> None:
        """Clear the conversation history."""
        self._message_history = []
        logger.debug("Conversation history cleared")

    def get_history(self) -> List[dict]:
        """Get conversation history as serializable dicts."""
        history = [
            {"role": msg.type, "content": msg.content}
            for msg in self._message_history
        ]
        logger.debug("get_history called (messages=%d)", len(history))
        return history

    def _get_input_messages(self, prompt: str) -> List:
        if self.maintain_history:
            return list(self._message_history) + [HumanMessage(content=prompt)]
        return [HumanMessage(content=prompt)]

    def _save_history(self, messages: List) -> None:
        if self.maintain_history:
            self._message_history = messages
