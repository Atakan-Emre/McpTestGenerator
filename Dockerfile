# QA-MCP: Test Standardization & Orchestration Server
# Multi-stage Dockerfile with dedicated production and development targets

FROM python:3.11-slim AS base

LABEL org.opencontainers.image.title="QA-MCP"
LABEL org.opencontainers.image.description="Test Standardization & Orchestration MCP Server"
LABEL org.opencontainers.image.version="1.0.2"
LABEL org.opencontainers.image.authors="Atakan Emre"
LABEL org.opencontainers.image.source="https://github.com/Atakan-Emre/McpTestGenerator"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY resources/ ./resources/

RUN pip install --no-cache-dir .

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_LEVEL=info \
    ENABLE_WRITE_TOOLS=false \
    AUDIT_LOG_ENABLED=true \
    HTTP_ENABLED=false \
    HTTP_BIND_HOST=127.0.0.1 \
    HTTP_PORT=8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import qa_mcp; print('OK')" || exit 1


FROM base AS production

RUN groupadd --gid 1000 qamcp && \
    useradd --uid 1000 --gid qamcp --shell /bin/bash --create-home qamcp && \
    chown -R qamcp:qamcp /app

USER qamcp

ENTRYPOINT ["python", "-m", "qa_mcp.server"]


FROM base AS development

COPY tests/ ./tests/

RUN pip install --no-cache-dir -e ".[dev]"

ENTRYPOINT ["python"]
CMD ["-m", "pytest", "tests/", "-v"]


FROM production AS final
