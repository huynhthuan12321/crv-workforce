# ===== Stage 1: Builder =====
FROM python:3.12-slim as builder

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

RUN uv venv /app/.venv && \
    . /app/.venv/bin/activate && \
    uv sync --frozen --no-dev

# ===== Stage 2: Runtime =====
FROM python:3.12-slim

WORKDIR /app

RUN groupadd -r appgroup && \
    useradd -r -g appgroup -d /app -s /sbin/nologin appuser

COPY --from=builder /app/.venv /app/.venv

COPY --chown=appuser:appgroup source/ ./source/
COPY --chown=appuser:appgroup migrations/ ./migrations/
COPY --chown=appuser:appgroup alembic.ini ./

RUN mkdir -p /app/source/data/error_logs /app/source/data/full_logs && \
    chown -R appuser:appgroup /app/source/data

USER appuser

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import socket; socket.create_connection(('localhost', 8000), timeout=5)" || exit 1

CMD ["python", "-m", "source"]
