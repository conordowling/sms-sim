FROM python:3.14-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

# Install dependencies first so this layer is cached across code changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY src/ ./src/

ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app/src
