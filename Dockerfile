# ─── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app
COPY pyproject.toml ./
COPY src/ ./src/

# Install dependencies into a virtual environment
RUN uv sync --no-dev --no-editable

# ─── Runtime stage ────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Install Docker CLI (needed to spin up sandbox containers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the virtual environment and source from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

# Make sure the venv binaries are on PATH
ENV PATH="/app/.venv/bin:$PATH"

# Non-root user for safety
RUN useradd --create-home --shell /bin/bash agent
USER agent

ENTRYPOINT ["python", "-m", "paca_agent"]
