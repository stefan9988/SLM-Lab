# SLM Lab

A modern AI chat interface with multi-agent support, document analysis, and real-time streaming.

## Features

- Real-time streaming chat with multiple LLM providers
- File attachment support (images, PDFs, documents — 10 MB per file, 20 MB total)
- Web search, web fetch, and Python code execution via agent tools
- Document analysis: extract structured data from documents using custom schemas
- Data validation: verify extracted facts against web sources
- Conversation history across sessions (Redis + PostgreSQL)
- Vector similarity search for document chunks (Qdrant)
- Model switching mid-conversation
- Multi-user support with Google OAuth
- Tool usage notifications shown in UI

## Supported LLM Providers

Each agent (general, document, validation) can use a different provider and model.

| Provider | `LLM_PROVIDER` value | Required env var |
|---|---|---|
| **Ollama** (local, default) | `ollama` | — |
| **OpenRouter** | `openrouter` | `OPEN_ROUTER_API_KEY` |
| **Anthropic** | `anthropic` | `ANTHROPIC_API_KEY` |

## Agent Overview

Three specialized agents run concurrently:

- **General Agent** — main conversational interface; has access to all tools; can delegate to other agents
- **Document Agent** — extracts structured data from documents against a user-defined schema
- **Validation Agent** — verifies extracted facts against web sources using search and fetch tools

Agents are configured via env vars. Tool toggles control which tools each agent can use. The validation agent can only be called by the general agent.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [Ollama](https://ollama.ai) running on the host (for local models), or an API key for OpenRouter/Anthropic
- A Google Cloud project with OAuth credentials (`GOOGLE_CLIENT_ID`) — required for login

## Setup

1. Copy the example env file and configure it:

```bash
cp .env.example .env
```

2. Set `GOOGLE_CLIENT_ID` to your Google OAuth client ID (required for login).

3. Set `LLM_PROVIDER` to `ollama`, `openrouter`, or `anthropic`, and add the relevant API key.

4. Pull your desired Ollama model (if using Ollama):

```bash
ollama pull qwen3:14b
```

5. To use Ollama cloud models or tools, sign in first:

```bash
ollama signin
```

## Running with Docker

```bash
docker compose up --build
```

- **Frontend:** `http://localhost:8080`
- **Backend API:** `http://localhost:8000`

The stack includes Redis, PostgreSQL, and Qdrant. Both backend and frontend use `network_mode: host`, so they share the host's network and can reach Ollama on `localhost:11434`, Redis on `localhost:6379`, and Qdrant on `localhost:6333` directly.

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

## Storage Services

### Redis (session persistence)

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
| `REDIS_URL` | `redis://default:slmlab@localhost:6379/0` | Redis connection URL |
| `REDIS_ENABLED` | `false` | Set to `true` to enable; Docker Compose enables it automatically |
| `REDIS_SESSION_TTL_DAYS` | `30` | Auto-expire inactive sessions after N days |

### PostgreSQL (long-term archive)

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
| `POSTGRES_ENABLED` | `false` | Set to `true` to enable; Docker Compose enables it automatically |
| `POSTGRES_USER` | `slmlab` | Database user |
| `POSTGRES_PASSWORD` | `slmlab` | Database password |
| `POSTGRES_DB` | `slmlab` | Database name |
| `POSTGRES_POOL_SIZE` | `5` | Connection pool size |
| `POSTGRES_MAX_OVERFLOW` | `10` | Max overflow connections |
| `POSTGRES_POOL_RECYCLE` | `3600` | Pool recycle interval (seconds) |
| `POSTGRES_POOL_PRE_PING` | `true` | Ping connections before use |

### Qdrant (vector database)

Qdrant provides vector similarity search for document chunk embeddings. When running with Docker Compose, Qdrant starts automatically.

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

## Configuration Reference

### Core

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `development` | Application environment (`development`, `production`) |
| `DEBUG` | `false` | Enable debug mode |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

### Authentication

| Variable | Default | Description |
|---|---|---|
| `GOOGLE_CLIENT_ID` | — | Google OAuth client ID (required for login) |
| `JWT_SECRET_KEY` | — | Secret key for signing JWTs (must be changed in production) |
| `JWT_EXPIRATION_HOURS` | `24` | JWT token lifetime in hours |

### LLM

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | LLM provider: `ollama`, `openrouter`, or `anthropic` |
| `MODEL_NAME` | `llama2` | Default model name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_THINKING` | `true` | Enable extended thinking for Ollama models that support it |
| `OLLAMA_API_KEY` | — | Optional API key for Ollama |
| `OPEN_ROUTER_API_KEY` | — | OpenRouter API key |
| `OPEN_ROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter base URL |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |

### Per-agent LLM overrides

Each agent can use a different provider and model. Leave empty to fall back to the global `LLM_PROVIDER` / `MODEL_NAME`.

| Variable | Default | Description |
|---|---|---|
| `GENERAL_AGENT_LLM_PROVIDER` | — | Provider override for the general agent |
| `GENERAL_AGENT_MODEL_NAME` | — | Model override for the general agent |
| `DOCUMENT_AGENT_LLM_PROVIDER` | — | Provider override for the document agent |
| `DOCUMENT_AGENT_MODEL_NAME` | — | Model override for the document agent |
| `VALIDATION_AGENT_LLM_PROVIDER` | — | Provider override for the validation agent |
| `VALIDATION_AGENT_MODEL_NAME` | — | Model override for the validation agent |

### Tool toggles

Each tool can be enabled or disabled per agent via env vars following the pattern `<AGENT>_<TOOL>=true|false`. Tools not listed for an agent are unavailable to it regardless of configuration.

**General Agent** (default values):

| Variable | Default |
|---|---|
| `GENERAL_AGENT_DATE_TIME_TOOL` | `true` |
| `GENERAL_AGENT_BRAVE_SEARCH_TOOL` | `true` |
| `GENERAL_AGENT_PYTHON_REPL_TOOL` | `true` |
| `GENERAL_AGENT_OLLAMA_WEB_SEARCH_TOOL` | `true` |
| `GENERAL_AGENT_OLLAMA_WEB_FETCH_TOOL` | `true` |
| `GENERAL_AGENT_READ_FILE_CONTENT_TOOL` | `true` |
| `GENERAL_AGENT_SEARCH_CHUNKS_TOOL` | `true` |
| `GENERAL_AGENT_DELEGATE_TOOL` | `false` |
| `GENERAL_AGENT_WEB_PAGE_CONTENT_TOOL` | `true` |

**Document Agent** (all off by default — it reads files directly via the extraction prompt):

| Variable | Default |
|---|---|
| `DOCUMENT_AGENT_DATE_TIME_TOOL` | `false` |
| `DOCUMENT_AGENT_BRAVE_SEARCH_TOOL` | `false` |
| `DOCUMENT_AGENT_PYTHON_REPL_TOOL` | `false` |
| `DOCUMENT_AGENT_OLLAMA_WEB_SEARCH_TOOL` | `false` |
| `DOCUMENT_AGENT_OLLAMA_WEB_FETCH_TOOL` | `false` |
| `DOCUMENT_AGENT_READ_FILE_CONTENT_TOOL` | `false` |
| `DOCUMENT_AGENT_SEARCH_CHUNKS_TOOL` | `false` |
| `DOCUMENT_AGENT_DELEGATE_TOOL` | `false` |
| `DOCUMENT_AGENT_WEB_PAGE_CONTENT_TOOL` | `false` |

**Validation Agent** (web tools enabled for fact-checking):

| Variable | Default |
|---|---|
| `VALIDATION_AGENT_DATE_TIME_TOOL` | `false` |
| `VALIDATION_AGENT_BRAVE_SEARCH_TOOL` | `true` |
| `VALIDATION_AGENT_OLLAMA_WEB_SEARCH_TOOL` | `false` |
| `VALIDATION_AGENT_OLLAMA_WEB_FETCH_TOOL` | `false` |
| `VALIDATION_AGENT_WEB_PAGE_CONTENT_TOOL` | `true` |

Note: `BRAVE_SEARCH_API_KEY` must be set for the Brave search tool to work.

### Embeddings

Embeddings require both `EMBEDDING_ENABLED=true` and `QDRANT_ENABLED=true`.

| Variable | Default | Description |
|---|---|---|
| `EMBEDDING_ENABLED` | `false` | Enable automatic embedding of uploaded files |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `EMBEDDING_DIMENSIONS` | `768` | Embedding vector dimensions |
| `EMBEDDING_CHUNK_SIZE` | `1000` | Token chunk size for splitting documents |
| `EMBEDDING_CHUNK_OVERLAP` | `200` | Overlap between consecutive chunks |

### File limits

File size limits are enforced server-side: 10 MB per individual file, 20 MB total per request.

### LangSmith (optional tracing)

| Variable | Default | Description |
|---|---|---|
| `LANGSMITH_TRACING` | `false` | Enable LangSmith tracing |
| `LANGSMITH_ENDPOINT` | `https://api.smith.langchain.com` | LangSmith API endpoint |
| `LANGSMITH_API_KEY` | — | LangSmith API key |
| `LANGSMITH_PROJECT` | `SLM Lab` | LangSmith project name |

## API Endpoints

All endpoints (except `/auth/google`) require a `Bearer` JWT in the `Authorization` header.

### Authentication

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/google` | Exchange a Google ID token for an app JWT |

### Chat

| Method | Path | Description |
|---|---|---|
| `POST` | `/chat` | Send a message and receive a complete response |
| `POST` | `/chat/stream` | Send a message and receive a streaming SSE response |
| `GET` | `/history` | Retrieve conversation history for a session (`?session_id=`) |
| `DELETE` | `/history` | Clear conversation history for a session (`?session_id=`) |

### Model management

| Method | Path | Description |
|---|---|---|
| `GET` | `/general-agent/model` | Get the current general agent provider and model |
| `PUT` | `/general-agent/model` | Switch the general agent to a different provider/model |
| `GET` | `/document-agent/model` | Get the current document agent provider and model |
| `PUT` | `/document-agent/model` | Switch the document agent to a different provider/model |

### Sessions

| Method | Path | Description |
|---|---|---|
| `GET` | `/sessions` | List all sessions with titles (for the sidebar) |

### Archive (PostgreSQL)

| Method | Path | Description |
|---|---|---|
| `GET` | `/archive/sessions` | List all archived sessions |
| `GET` | `/archive/sessions/{id}` | Get full message history for a session |
| `DELETE` | `/archive/sessions/{id}` | Delete an archived session |

### Extraction schemas

| Method | Path | Description |
|---|---|---|
| `GET` | `/schemas` | List all extraction schemas for the current user |
| `POST` | `/schemas` | Create a new extraction schema |
| `PUT` | `/schemas/{schema_id}` | Update an extraction schema |
| `DELETE` | `/schemas/{schema_id}` | Delete an extraction schema |

### Document analysis

| Method | Path | Description |
|---|---|---|
| `POST` | `/analyze` | Analyze a document against a schema; streams SSE events |

### Validation

| Method | Path | Description |
|---|---|---|
| `POST` | `/validate-stream` | Validate extracted fields against URLs; streams SSE events |
| `GET` | `/validate-results/{session_id}` | Get persisted validation results for a session |

## Local Development (without Docker)

### Backend

```bash
uv sync
uv run uvicorn BE.app:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd FE && npm install && npm run dev
```

The frontend runs at `http://localhost:3000` by default. Set `VITE_API_URL=http://localhost:8000` in `.env` to point it at the local backend.

### Running Tests

```bash
# Backend
uv run pytest

# Frontend
cd FE && npx vitest run

# Format
uv run black .
```
