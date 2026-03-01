"""LangGraph-based reactive agent wrapper."""

import json
from typing import AsyncIterator, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from BE.logger import setup_logger
from BE.session_store import SessionStore, InMemoryStore, warm_session_from_archive

logger = setup_logger(__name__)


class Agent:
    """Provider-agnostic agent using LangChain's create_agent."""

    def __init__(
        self,
        llm: BaseChatModel,
        system_prompt: Optional[str] = None,
        tools: Optional[List[BaseTool]] = None,
        maintain_history: bool = False,
        session_store: Optional[SessionStore] = None,
        model_name: str = "",
        provider: str = "",
        agent_name: str = "",
    ):
        self.maintain_history = maintain_history
        self._store: SessionStore = session_store or InMemoryStore()
        self._model_name = model_name
        self._provider = provider
        self._agent_name = agent_name

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

    async def invoke(
        self,
        prompt: str,
        session_id: str,
        images: Optional[list[dict]] = None,
        file_attachments: Optional[list[dict]] = None,
        user_id: str = "",
    ) -> str:
        """Get a complete response for the given prompt."""
        logger.info(
            "invoke called (prompt_length=%d, session_id=%s)", len(prompt), session_id
        )
        logger.debug("invoke prompt: %.200s", prompt)
        try:
            messages = await self._get_input_messages(
                prompt,
                session_id,
                images=images,
                file_attachments=file_attachments,
                user_id=user_id,
            )
            configurable: dict = {}
            if user_id:
                configurable["user_id"] = user_id
            if self._agent_name:
                configurable["agent_name"] = self._agent_name
            config = {"configurable": configurable} if configurable else None
            result = await self._agent.ainvoke({"messages": messages}, config=config)
            all_messages = result["messages"]
            await self._save_history(all_messages, session_id, user_id=user_id)
            response = all_messages[-1].content
            logger.info("invoke complete (response_length=%d)", len(response))
            return response
        except Exception:
            logger.error("invoke failed", exc_info=True)
            raise

    async def stream(
        self,
        prompt: str,
        session_id: str,
        images: Optional[list[dict]] = None,
        file_attachments: Optional[list[dict]] = None,
        user_id: str = "",
    ):
        logger.info(
            "stream called (prompt_length=%d, session_id=%s)", len(prompt), session_id
        )
        logger.debug("stream prompt: %.200s", prompt)
        try:
            messages = await self._get_input_messages(
                prompt,
                session_id,
                images=images,
                file_attachments=file_attachments,
                user_id=user_id,
            )

            full_response = []
            full_thinking = ""
            chunk_count = 0
            thinking_started = False
            tool_messages = []
            pending_tool_calls = {}  # {index: {"name": str, "args": str}}
            completed_tools = []  # [{"name": str, "args": dict}, ...]
            configurable: dict = {}
            if user_id:
                configurable["user_id"] = user_id
            if self._agent_name:
                configurable["agent_name"] = self._agent_name
            config = {"configurable": configurable} if configurable else None
            async for stream_mode, chunk in self._agent.astream(
                {"messages": messages},
                config=config,
                stream_mode=["messages", "custom"],
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
                            full_thinking += thinking_content
                            yield {"type": "thinking", "content": thinking_content}

                        if msg_chunk.tool_call_chunks:
                            for tc in msg_chunk.tool_call_chunks:
                                idx = tc.get("index", 0)
                                if tc.get("name"):
                                    pending_tool_calls[idx] = {
                                        "name": tc["name"],
                                        "args": "",
                                    }
                                    logger.info("Tool call: %s", tc["name"])
                                    yield {
                                        "type": "status",
                                        "content": f"Calling tool: {tc['name']}",
                                    }
                                if tc.get("args") and idx in pending_tool_calls:
                                    pending_tool_calls[idx]["args"] += tc["args"]
                        elif msg_chunk.content:
                            content = msg_chunk.content
                            if isinstance(content, list):
                                # Anthropic newer models return content blocks: [{"type": "text", "text": "..."}]
                                text = "".join(
                                    block.get("text", "")
                                    for block in content
                                    if isinstance(block, dict)
                                    and block.get("type") == "text"
                                )
                            else:
                                # Ollama / OpenRouter / older Claude return plain strings
                                text = content
                            if text:
                                full_response.append(text)
                                chunk_count += 1
                                yield {"type": "token", "content": text}
                    elif isinstance(msg_chunk, ToolMessage):
                        tool_messages.append(msg_chunk)
                        for idx in sorted(pending_tool_calls):
                            info = pending_tool_calls[idx]
                            try:
                                args = json.loads(info["args"]) if info["args"] else {}
                            except json.JSONDecodeError:
                                args = {}
                            completed_tools.append({"name": info["name"], "args": args})
                            yield {
                                "type": "tool_use",
                                "content": json.dumps(
                                    {"name": info["name"], "args": args}
                                ),
                            }
                        pending_tool_calls.clear()
                        yield {"type": "status", "content": "Tool returned result"}

            ai_msg = AIMessage(content="".join(full_response))
            if full_thinking:
                ai_msg.additional_kwargs["thinking"] = full_thinking
            if completed_tools:
                ai_msg.additional_kwargs["tools_used"] = completed_tools
            all_messages = list(messages) + tool_messages + [ai_msg]
            await self._save_history(all_messages, session_id, user_id=user_id)
            logger.info("stream complete (chunks=%d)", chunk_count)
        except Exception:
            logger.error("stream failed", exc_info=True)
            raise

    async def warm_session(self, session_id: str, user_id: str = "") -> None:
        """Load session history from the archive if the session store is empty."""
        await warm_session_from_archive(self._store, session_id, user_id=user_id)

    async def append_to_history(
        self, session_id: str, messages: list, user_id: str = ""
    ) -> None:
        """Append LangChain messages to the existing session history."""
        await self.warm_session(session_id, user_id=user_id)
        existing = await self._store.get_messages(session_id, user_id=user_id)
        all_messages = list(existing) + list(messages)
        await self._store.save_messages(
            session_id, all_messages, self._model_name, self._provider, user_id=user_id
        )

    async def clear_history(self, session_id: str, user_id: str = "") -> None:
        """Clear the conversation history for a session."""
        await self._store.clear(session_id, user_id=user_id)
        logger.debug("Conversation history cleared (session_id=%s)", session_id)

    async def get_history(self, session_id: str, user_id: str = "") -> List[dict]:
        """Get conversation history as serializable dicts for a session."""
        history = await self._store.get_history_dicts(session_id, user_id=user_id)
        logger.debug(
            "get_history called (session_id=%s, messages=%d)", session_id, len(history)
        )
        return history

    async def _get_input_messages(
        self,
        prompt: str,
        session_id: str,
        images: Optional[list[dict]] = None,
        file_attachments: Optional[list[dict]] = None,
        user_id: str = "",
    ) -> List:
        additional_kwargs = {}
        if file_attachments:
            additional_kwargs["file_attachments"] = file_attachments

        if images:
            content: list[dict] = [{"type": "text", "text": prompt}]
            for img in images:
                content.append({"type": "image_url", "image_url": {"url": img["url"]}})
            human_msg = HumanMessage(
                content=content, additional_kwargs=additional_kwargs
            )
        else:
            human_msg = HumanMessage(
                content=prompt, additional_kwargs=additional_kwargs
            )

        if self.maintain_history:
            history = await self._store.get_messages(session_id, user_id=user_id)
            return list(history) + [human_msg]
        return [human_msg]

    async def _save_history(
        self, messages: List, session_id: str, user_id: str = ""
    ) -> None:
        if self.maintain_history:
            await self._store.save_messages(
                session_id, messages, self._model_name, self._provider, user_id=user_id
            )
