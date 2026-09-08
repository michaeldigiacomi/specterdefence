# Multi-stage Dockerfile for SpecterDefence
# Builds backend (with optional frontend) - backend targets: production, development

# ============================================
# Stage 1: Backend production
# ============================================
FROM python:3.13.1-slim AS backend-production

ARG GIT_SHA=dev

WORKDIR /app

# Install build tools and create app user
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8.3

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install Python dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --only main

# Copy source code
COPY --chown=app:app src/ ./src/

# Set environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    GIT_SHA=${GIT_SHA}

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ============================================
# Stage 2: Backend with frontend production
# ============================================
FROM node:22.9-alpine AS frontend-builder

ARG GIT_SHA=dev
ENV VITE_GIT_SHA=${GIT_SHA}

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build:docker

FROM backend-production AS backend-frontend-production

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist/

# ============================================
# Stage 3: Backend development
# ============================================
FROM python:3.13.1-slim AS backend-development

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8.3

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install all dependencies including dev
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

# Copy application code
COPY src/ ./src/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ============================================
# Default: backend-production
# ============================================
FROM backend-production
