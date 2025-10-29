# =============================================================================
# Emerald Finance Platform - Backend Dockerfile
# =============================================================================
# Multi-stage build for production-ready container
# Uses uv for fast dependency installation

# -----------------------------------------------------------------------------
# Stage 1: Builder
# -----------------------------------------------------------------------------
FROM python:3.13-slim AS builder

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
# --no-dev excludes development dependencies
RUN uv sync --frozen --no-dev

# -----------------------------------------------------------------------------
# Stage 2: Runtime
# -----------------------------------------------------------------------------
FROM python:3.13-slim

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 emerald && \
    mkdir -p /app /app/logs && \
    chown -R emerald:emerald /app

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=emerald:emerald /app/.venv /app/.venv

# Copy application code
COPY --chown=emerald:emerald src/ /app/src/
COPY --chown=emerald:emerald alembic/ /app/alembic/
COPY --chown=emerald:emerald alembic.ini /app/

# Switch to non-root user
USER emerald

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
