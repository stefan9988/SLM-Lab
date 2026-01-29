"""FastAPI chat server exposing OllamaAgent via HTTP endpoints."""

import json
import sys
from pathlib import Path

# Add src directory to path for imports when running from project root
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from prompts.general_agent_prompt import GENERAL_AGENT_PROMPT

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents import init_ollama_agent
from config import settings
from tools import get_current_date_and_time, brave_search_tool

app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
)

general_agent = init_ollama_agent(system_prompt=GENERAL_AGENT_PROMPT, tools=[get_current_date_and_time, brave_search_tool], maintain_history=True)

class ChatRequest(BaseModel):
    """Request model for chat endpoints."""

    message: str


@app.post("/chat")
async def chat(request: ChatRequest):
    """Send a message and get a complete response.

    Args:
        request: ChatRequest containing the user's message.

    Returns:
        JSON with the assistant's response.
    """
    response = general_agent.invoke(request.message)
    return {"response": response}


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Send a message and get a streaming SSE response.

    Args:
        request: ChatRequest containing the user's message.

    Returns:
        Server-Sent Events stream of response chunks.
    """

    def generate():
        for event in general_agent.stream(request.message):
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/history")
async def get_history():
    """Retrieve conversation history.

    Returns:
        JSON with the conversation history.
    """
    return {"history": general_agent.get_history()}


@app.delete("/history")
async def clear_history():
    """Clear conversation history.

    Returns:
        JSON with status confirmation.
    """
    general_agent.clear_history()
    return {"status": "cleared"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
