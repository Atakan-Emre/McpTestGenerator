# QA-MCP: Test Standardization & Orchestration Server
# Multi-arch Docker image (amd64/arm64)

# =============================================================================
# Build stage
# =============================================================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir build && \
    pip install --no-cache-dir .

# =============================================================================
# Production stage
# =============================================================================
FROM python:3.11-slim as production

# Labels for container metadata
LABEL org.opencontainers.image.title="QA-MCP"
LABEL org.opencontainers.image.description="Test Standardization & Orchestration MCP Server"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.authors="QA-MCP Team"
LABEL org.opencontainers.image.source="https://github.com/qa-mcp/qa-mcp"
LABEL org.opencontainers.image.licenses="MIT"

# Create non-root user for security
RUN groupadd --gid 1000 qamcp && \
    useradd --uid 1000 --gid qamcp --shell /bin/bash --create-home qamcp

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=qamcp:qamcp src/qa_mcp /app/qa_mcp
COPY --chown=qamcp:qamcp resources /app/resources

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    # QA-MCP specific
    LOG_LEVEL=info \
    ENABLE_WRITE_TOOLS=false \
    AUDIT_LOG_ENABLED=true \
    # Security: disable HTTP by default
    HTTP_ENABLED=false \
    HTTP_BIND_HOST=127.0.0.1 \
    HTTP_PORT=8080

# Switch to non-root user
USER qamcp

# Health check (for container orchestration)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import qa_mcp; print('OK')" || exit 1

# Default command: run MCP server in stdio mode
ENTRYPOINT ["python", "-m", "qa_mcp.server"]

# =============================================================================
# Development stage (optional)
# =============================================================================
FROM production as development

USER root

# Install development dependencies
RUN pip install --no-cache-dir pytest pytest-asyncio pytest-cov ruff mypy

USER qamcp

# Override entrypoint for development
ENTRYPOINT ["/bin/bash"]
