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

### Using Ollama cloud models

To use Ollama cloud models or tools, you must sign in and set up your API and device keys:

```bash
ollama signin
```

## Running with Docker

```bash
docker compose up --build
```

- **Frontend:** `http://localhost:8080`
- **Backend API:** `http://localhost:8000`

The stack includes Redis for persistent session/conversation history and Qdrant for vector similarity search. Both backend and frontend use `network_mode: host`, so they share the host's network. This allows the backend to reach Ollama on `localhost:11434`, Redis on `localhost:6379`, and Qdrant on `localhost:6333` directly.

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

## PostgreSQL (long-term archive)

In addition to Redis (short-term session state with TTL), PostgreSQL stores the full conversation history permanently — messages are never expired.

When running with Docker Compose, PostgreSQL starts automatically. For local development:

```bash
docker run -d -p 5432:5432 -e POSTGRES_USER=slmlab -e POSTGRES_PASSWORD=slmlab -e POSTGRES_DB=slmlab postgres:16-alpine
```

Or disable it in `.env`:

```
POSTGRES_ENABLED=false
```

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_URL` | `postgresql+asyncpg://slmlab:slmlab@localhost:5432/slmlab` | PostgreSQL connection URL |
| `POSTGRES_ENABLED` | `true` | Set to `false` to disable archiving |

### Archive API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/archive/sessions` | List all archived sessions |
| `GET` | `/archive/sessions/{id}` | Get full message history for a session |
| `DELETE` | `/archive/sessions/{id}` | Delete an archived session |

## Qdrant (vector database)

Qdrant provides vector similarity search for embeddings. When running with Docker Compose, Qdrant starts automatically.

For local development, either start Qdrant separately:

```bash
docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

Or disable it in `.env`:

```
QDRANT_ENABLED=false
```

| Variable | Default | Description |
|---|---|---|
| `QDRANT_URL` | `http://localhost:6333` | Qdrant HTTP API URL |
| `QDRANT_ENABLED` | `false` | Set to `true` to enable vector database |
| `QDRANT_API_KEY` | `slmlab` | API key for Qdrant authentication |
| `QDRANT_COLLECTION_NAME` | `slmlab` | Default collection name |
| `QDRANT_GRPC_PORT` | `6334` | Qdrant gRPC port |

## Local development (without Docker)

### Backend

```bash
uv sync
uv run uvicorn BE.app:app --host 0.0.0.0 --port 8000 --reload
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
