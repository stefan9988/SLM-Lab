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

Both services use `network_mode: host`, so they share the host's network. This allows the backend to reach Ollama on `localhost:11434` directly.

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
