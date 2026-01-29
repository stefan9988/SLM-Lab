"""FastAPI chat server exposing OllamaAgent via HTTP endpoints."""

import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Add src directory to path for imports when running from project root
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from prompts.general_agent_prompt import GENERAL_AGENT_PROMPT

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ValidationError

from agents import init_ollama_agent
from config import settings
from logger import setup_logger
from tools import get_current_date_and_time, brave_search_tool, python_repl_tool

logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup")
    yield
    logger.info("Application shutdown")


app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    lifespan=lifespan,
)

general_agent = init_ollama_agent(system_prompt=GENERAL_AGENT_PROMPT, tools=[get_current_date_and_time, brave_search_tool, python_repl_tool], maintain_history=True)

class ChatRequest(BaseModel):
    """Request model for chat endpoints."""

    message: str


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    logger.warning("Validation error: %s", exc)
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.post("/chat")
async def chat(request: ChatRequest):
    """Send a message and get a complete response."""
    logger.info("POST /chat (message_preview=%.50s)", request.message)
    response = general_agent.invoke(request.message)
    logger.info("POST /chat response (length=%d)", len(response))
    return {"response": response}


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Send a message and get a streaming SSE response."""
    logger.info("POST /chat/stream (message_preview=%.50s)", request.message)

    def generate():
        for event in general_agent.stream(request.message):
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: [DONE]\n\n"
        logger.info("POST /chat/stream complete")

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/history")
async def get_history():
    """Retrieve conversation history."""
    logger.info("GET /history")
    history = general_agent.get_history()
    logger.info("GET /history (messages=%d)", len(history))
    return {"history": history}


@app.delete("/history")
async def clear_history():
    """Clear conversation history."""
    logger.info("DELETE /history")
    general_agent.clear_history()
    return {"status": "cleared"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
