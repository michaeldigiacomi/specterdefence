.PHONY: help install install-dev test test-cov test-unit test-integration test-ci lint lint-fix format format-check type-check security-check quality quality-fix clean docker-build docker-run migrate migration pre-commit

# =============================================================================
# SpecterDefence Makefile
# =============================================================================
# Use 'make help' to see all available targets
# =============================================================================

# Default target
help:
	@echo "╔══════════════════════════════════════════════════════════════════╗"
	@echo "║              SpecterDefence - Available Targets                  ║"
	@echo "╚══════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "  📦 Setup:"
	@echo "    install        Install production dependencies"
	@echo "    install-dev    Install development dependencies + pre-commit"
	@echo "    pre-commit     Install pre-commit hooks"
	@echo ""
	@echo "  🧪 Testing:"
	@echo "    test           Run all tests with coverage"
	@echo "    test-cov       Run all tests with HTML/XML coverage reports"
	@echo "    test-unit      Run unit tests only"
	@echo "    test-integration Run integration tests only"
	@echo "    test-ci        Run tests for CI (with strict coverage)"
	@echo ""
	@echo "  🔍 Code Quality (ZERO TOLERANCE):"
	@echo "    lint           Run ruff linter (STRICT - fails on any error)"
	@echo "    lint-fix       Run ruff with auto-fix"
	@echo "    format         Format code with black"
	@echo "    format-check   Check formatting (CI mode)"
	@echo "    type-check     Run mypy type checker (STRICT mode)"
	@echo "    import-check   Check import sorting"
	@echo "    security-check Run bandit security scanner"
	@echo "    quality        Run ALL quality checks (lint + format-check + type-check)"
	@echo "    quality-fix    Auto-fix all fixable issues"
	@echo ""
	@echo "  🗄️  Database:"
	@echo "    migrate        Run database migrations"
	@echo "    migration      Create a new migration (make migration msg='description')"
	@echo ""
	@echo "  🐳 Docker:"
	@echo "    docker-build   Build Docker image"
	@echo "    docker-run     Run Docker container"
	@echo ""
	@echo "  🚀 Development:"
	@echo "    run            Run the development server with auto-reload"
	@echo "    run-prod       Run production server"
	@echo ""
	@echo "  🧹 Utilities:"
	@echo "    clean          Clean up generated files and caches"
	@echo "    clean-all      Clean + remove virtual environment"
	@echo ""
	@echo "  📋 Validation (run before committing):"
	@echo "    validate       Full validation suite (quality + test)"

# =============================================================================
# Installation
# =============================================================================

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install
	@echo "✅ Development dependencies installed and pre-commit hooks configured"

pre-commit:
	pre-commit install
	@echo "✅ Pre-commit hooks installed"

# =============================================================================
# Testing
# =============================================================================

test:
	pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html --cov-fail-under=75

test-cov:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=xml --cov-report=term-missing

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v -m integration

test-ci:
	pytest tests/ -v --cov=src --cov-report=xml --cov-report=term --cov-fail-under=75 --strict-markers

# =============================================================================
# Code Quality - STRICT MODE (Zero Tolerance)
# =============================================================================

lint:
	@echo "🔍 Running Ruff Linter (STRICT MODE)..."
	ruff check .
	@echo "✅ Ruff linting passed"

lint-fix:
	@echo "🔧 Running Ruff with Auto-fix..."
	ruff check . --fix
	@echo "✅ Ruff auto-fix complete"

format:
	@echo "🎨 Formatting code with Black..."
	black .
	@echo "✅ Code formatted"

format-check:
	@echo "🔍 Checking Black formatting (CI mode)..."
	black --check --diff .
	@echo "✅ Black formatting check passed"

type-check:
	@echo "🔍 Running MyPy Type Checker (STRICT MODE)..."
	mypy src/ tests/ --strict
	@echo "✅ Type checking passed"

import-check:
	@echo "🔍 Checking import sorting..."
	ruff check . --select I
	@echo "✅ Import sorting check passed"

security-check:
	@echo "🔒 Running Bandit Security Scanner..."
	bandit -r src/ -f screen
	@echo "✅ Security scan complete"

# Run ALL quality checks (what CI runs)
quality: lint format-check type-check import-check
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════════════╗"
	@echo "║           ✅ ALL QUALITY CHECKS PASSED                          ║"
	@echo "╚══════════════════════════════════════════════════════════════════╝"

# Auto-fix all fixable issues
quality-fix: lint-fix format
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════════════╗"
	@echo "║        ✅ Auto-fixes applied - run 'make quality' to verify      ║"
	@echo "╚══════════════════════════════════════════════════════════════════╝"

# =============================================================================
# Database
# =============================================================================

migrate:
	alembic upgrade head

migration:
	@read -p "Migration message: " MSG; \
	alembic revision --autogenerate -m "$$MSG"

# =============================================================================
# Docker
# =============================================================================

docker-build:
	docker build -t specterdefence:latest .

docker-run:
	docker run -p 8000:8000 --env-file .env specterdefence:latest

# =============================================================================
# Development Server
# =============================================================================

run:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

run-prod:
	uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4

# =============================================================================
# Full Validation (run this before committing)
# =============================================================================

validate: quality test
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════════════╗"
	@echo "║     ✅ FULL VALIDATION PASSED - Ready to commit!                 ║"
	@echo "╚══════════════════════════════════════════════════════════════════╝"

# =============================================================================
# Cleanup
# =============================================================================

clean:
	@echo "🧹 Cleaning up..."
	rm -rf __pycache__ */__pycache__ */*/__pycache__ */*/*/__pycache__
	rm -rf .pytest_cache .coverage htmlcov coverage.xml
	rm -rf build/ dist/ *.egg-info
	rm -rf .mypy_cache .ruff_cache
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name ".DS_Store" -delete
	@echo "✅ Cleanup complete"

clean-all: clean
	@echo "🧹 Removing virtual environment..."
	rm -rf .venv venv
	@echo "✅ Full cleanup complete"
