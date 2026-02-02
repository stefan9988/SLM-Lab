# SLM Lab

A chat interface for testing Ollama (and OpenRouter) models, with tool support for web search, web fetch, code execution, and more.

## Prerequisites

- [Ollama](https://ollama.ai) running on the host
- [Docker](https://docs.docker.com/get-docker/) and Docker Compose

## Setup

1. Copy the example env file and configure it:

```bash
cp .env.example .env
```

Edit `.env` to set your model, API keys, and other settings. See `.env.example` for available options.

2. Pull your desired Ollama model:

```bash
ollama pull qwen3:14b
```

## Running with Docker

```bash
docker compose up --build
```

- **Frontend:** `http://localhost:8080`
- **Backend API:** `http://localhost:8000`

The stack includes a Redis container for persistent session/conversation history. Both backend and frontend use `network_mode: host`, so they share the host's network. This allows the backend to reach Ollama on `localhost:11434` and Redis on `localhost:6379` directly.

To stop:

```bash
docker compose down
```

### Remote access

If you're SSH'd into the server, access the UI from your local machine via SSH tunnel:

```bash
ssh -L 8080:localhost:8080 user@your-server
```

Then open `http://localhost:8080` in your browser.

## Redis (session persistence)

Conversation history is stored in Redis so it survives backend restarts. When running with Docker Compose, Redis starts automatically.

For local development, either start Redis separately:

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

Or disable it in `.env` to use in-memory storage (history lost on restart):

```
REDIS_ENABLED=false
```

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `REDIS_ENABLED` | `true` | Set to `false` to use in-memory fallback |
| `REDIS_SESSION_TTL_DAYS` | `30` | Auto-expire inactive sessions after N days |

## Local development (without Docker)

### Backend

```bash
uv sync
uv run uvicorn BE.app:app --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd FE
npm install
npm run dev
```

### Running tests

```bash
uv sync
uv run pytest tests/
```
