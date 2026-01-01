# QA-MCP: Test Standardization & Orchestration Server
# Multi-arch Docker image (amd64/arm64)

FROM python:3.11-slim

# Labels for container metadata
LABEL org.opencontainers.image.title="QA-MCP"
LABEL org.opencontainers.image.description="Test Standardization & Orchestration MCP Server"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.authors="Atakan Emre"
LABEL org.opencontainers.image.source="https://github.com/Atakan-Emre/McpTestGenerator"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Install dependencies first (for better caching)
RUN pip install --no-cache-dir --upgrade pip

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY resources/ ./resources/

# Install the package
RUN pip install --no-cache-dir .

# Create non-root user for security
RUN groupadd --gid 1000 qamcp && \
    useradd --uid 1000 --gid qamcp --shell /bin/bash --create-home qamcp && \
    chown -R qamcp:qamcp /app

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_LEVEL=info \
    ENABLE_WRITE_TOOLS=false \
    AUDIT_LOG_ENABLED=true \
    HTTP_ENABLED=false \
    HTTP_BIND_HOST=127.0.0.1 \
    HTTP_PORT=8080

# Switch to non-root user
USER qamcp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import qa_mcp; print('OK')" || exit 1

# Default command: run MCP server in stdio mode
ENTRYPOINT ["python", "-m", "qa_mcp.server"]
