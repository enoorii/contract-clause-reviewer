# Stage 1: Base with dependencies
FROM python:3.14-slim AS base
WORKDIR /app
COPY --from=astral/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

# Stage 2: Common runtime setup
FROM python:3.14-slim AS runtime-base

WORKDIR /app

# Install system dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        gosu \
        # WeasyPrint dependencies
        libgobject-2.0-0 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libcairo2 \
        libharfbuzz0b \
        libffi-dev \
    && \
    rm -rf /var/lib/apt/lists/*

# Create application user
RUN groupadd --gid 10001 appgroup && \
    useradd \
    --uid 10001 \
    --gid appgroup \
    --home-dir /app \
    --create-home \
    --shell /usr/sbin/nologin \
    appuser

# Create necessary directories (within /app)
RUN mkdir -p /app/data /app/reports /app/logs && \
    chown -R appuser:appgroup /app

# Copy virtual environment from base
COPY --from=base --chown=appuser:appgroup /app/.venv/ .venv/

# Copy application code
COPY --chown=appuser:appgroup app/ app/
COPY --chown=appuser:appgroup alembic/ alembic/
COPY --chown=appuser:appgroup alembic.ini .
COPY --chown=appuser:appgroup .env .

# Copy entrypoint script
COPY entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh


# API specific stage
FROM runtime-base AS api

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

ENTRYPOINT ["entrypoint.sh"]
CMD ["/app/.venv/bin/python", "-m", "granian", "--interface", "asgi", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Celery worker specific stage
FROM runtime-base AS celery-worker

# Celery doesn't need to expose ports
# No HEALTHCHECK needed for worker

ENTRYPOINT ["entrypoint.sh"]
CMD ["/app/.venv/bin/python", "-m", "celery", "-A", "app.core.celery:celery_app", "worker", "--beat", "--loglevel", "info", "-Q", "analysis,cleanup"]
