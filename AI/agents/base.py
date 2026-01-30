"""LangGraph-based reactive agent wrapper."""

from typing import Iterator, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from BE.logger import setup_logger

logger = setup_logger(__name__)


class Agent:
    """Provider-agnostic agent using LangChain's create_agent."""

    def __init__(
        self,
        llm: BaseChatModel,
        system_prompt: Optional[str] = None,
        tools: Optional[List[BaseTool]] = None,
        maintain_history: bool = False,
    ):
        self.maintain_history = maintain_history
        self._session_histories: dict[str, List] = {}

        tool_names = [t.name for t in tools] if tools else []
        logger.info(
            "Initializing Agent (model=%s, tools=%s)",
            llm.__class__.__name__,
            tool_names,
        )

        try:
            self._agent = create_agent(
                model=llm,
                tools=tools or [],
                system_prompt=system_prompt,
            )
            logger.info("Agent initialized successfully")
        except Exception:
            logger.error("Failed to initialize Agent", exc_info=True)
            raise

    def invoke(
        self,
        prompt: str,
        session_id: str,
        images: Optional[list[dict]] = None,
    ) -> str:
        """Get a complete response for the given prompt."""
        logger.info(
            "invoke called (prompt_length=%d, session_id=%s)", len(prompt), session_id
        )
        logger.debug("invoke prompt: %s", prompt)
        try:
            messages = self._get_input_messages(prompt, session_id, images=images)
            result = self._agent.invoke({"messages": messages})
            all_messages = result["messages"]
            self._save_history(all_messages, session_id)
            response = all_messages[-1].content
            logger.info("invoke complete (response_length=%d)", len(response))
            return response
        except Exception:
            logger.error("invoke failed", exc_info=True)
            raise

    def stream(
        self,
        prompt: str,
        session_id: str,
        images: Optional[list[dict]] = None,
    ):
        logger.info(
            "stream called (prompt_length=%d, session_id=%s)", len(prompt), session_id
        )
        logger.debug("stream prompt: %s", prompt)
        try:
            messages = self._get_input_messages(prompt, session_id, images=images)

            full_response = []
            token_count = 0
            thinking_started = False
            for stream_mode, chunk in self._agent.stream(
                {"messages": messages}, stream_mode=["messages", "custom"]
            ):
                if stream_mode == "custom":
                    yield {"type": "status", "content": chunk}
                elif stream_mode == "messages":
                    msg_chunk, metadata = chunk
                    if isinstance(msg_chunk, AIMessageChunk):
                        # Detect thinking content from thinking models (e.g. Qwen3)
                        thinking_content = msg_chunk.additional_kwargs.get(
                            "reasoning_content"
                        )
                        if thinking_content:
                            if not thinking_started:
                                thinking_started = True
                            yield {"type": "thinking", "content": thinking_content}

                        if msg_chunk.tool_call_chunks:
                            for tc in msg_chunk.tool_call_chunks:
                                if tc.get("name"):
                                    logger.info("Tool call: %s", tc["name"])
                                    yield {
                                        "type": "status",
                                        "content": f"Calling tool: {tc['name']}",
                                    }
                        elif msg_chunk.content:
                            full_response.append(msg_chunk.content)
                            token_count += 1
                            yield {"type": "token", "content": msg_chunk.content}
                    elif isinstance(msg_chunk, ToolMessage):
                        yield {"type": "status", "content": "Tool returned result"}

            all_messages = list(messages) + [AIMessage(content="".join(full_response))]
            self._save_history(all_messages, session_id)
            logger.info("stream complete (tokens=%d)", token_count)
        except Exception:
            logger.error("stream failed", exc_info=True)
            raise

    def clear_history(self, session_id: str) -> None:
        """Clear the conversation history for a session."""
        self._session_histories.pop(session_id, None)
        logger.debug("Conversation history cleared (session_id=%s)", session_id)

    def get_history(self, session_id: str) -> List[dict]:
        """Get conversation history as serializable dicts for a session."""
        messages = self._session_histories.get(session_id, [])
        history = [{"role": msg.type, "content": msg.content} for msg in messages]
        logger.debug(
            "get_history called (session_id=%s, messages=%d)", session_id, len(history)
        )
        return history

    def _get_input_messages(
        self,
        prompt: str,
        session_id: str,
        images: Optional[list[dict]] = None,
    ) -> List:
        if images:
            content: list[dict] = [{"type": "text", "text": prompt}]
            for img in images:
                content.append({"type": "image_url", "image_url": {"url": img["url"]}})
            human_msg = HumanMessage(content=content)
        else:
            human_msg = HumanMessage(content=prompt)

        if self.maintain_history:
            history = self._session_histories.get(session_id, [])
            return list(history) + [human_msg]
        return [human_msg]

    def _save_history(self, messages: List, session_id: str) -> None:
        if self.maintain_history:
            self._session_histories[session_id] = messages
