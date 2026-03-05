# Multi-stage Dockerfile for SpecterDefence
# Builds both the React frontend and Python backend

# ============================================
# Stage 1: Build the React frontend
# ============================================
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

# Copy package files first for better layer caching
COPY frontend/package.json frontend/package-lock.json* ./

# Install dependencies
RUN npm build:ci

# Copy frontend source code
COPY frontend/ ./

# Build the frontend for production
RUN npm run build

# ============================================
# Stage 2: Production image
# ============================================
FROM python:3.12-slim AS production

WORKDIR /app

# Install build dependencies and create user in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip list | grep msal

# Copy application code
COPY --chown=app:app src/ ./src/

# Copy built frontend from frontend-builder
COPY --from=frontend-builder --chown=app:app /app/frontend/dist ./frontend/dist/

# Set environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ============================================
# Stage 3: Development image
# ============================================
FROM python:3.12-slim AS development

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install with dev dependencies
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir pytest pytest-asyncio black ruff mypy pre-commit

# Copy application code
COPY src/ ./src/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
