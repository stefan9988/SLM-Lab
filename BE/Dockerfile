FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        libmupdf-dev \
        libfreetype6-dev \
        libharfbuzz-dev \
        libjbig2dec0-dev \
        libjpeg62-turbo-dev \
        libopenjp2-7-dev \
        libgumbo-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN useradd --create-home appuser

WORKDIR /app
RUN chown appuser:appuser /app

COPY pyproject.toml uv.lock ./
RUN chown appuser:appuser pyproject.toml uv.lock

USER appuser

RUN uv sync --frozen --no-dev --no-install-project

COPY --chown=appuser:appuser BE/ BE/
COPY --chown=appuser:appuser AI/ AI/

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "BE.app:app", "--host", "0.0.0.0", "--port", "8000"]
