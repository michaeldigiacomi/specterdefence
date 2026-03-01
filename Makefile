.PHONY: help install install-dev test test-cov test-unit test-integration test-ci lint lint-fix format format-check type-check clean docker-build docker-run migrate migration

# Default target
help:
	@echo "SpecterDefence - Available targets:"
	@echo ""
	@echo "  Setup:"
	@echo "    install        Install production dependencies"
	@echo "    install-dev    Install development dependencies"
	@echo ""
	@echo "  Testing:"
	@echo "    test           Run all tests with coverage"
	@echo "    test-cov       Run all tests with HTML and XML coverage reports"
	@echo "    test-unit      Run unit tests only"
	@echo "    test-integration Run integration tests only"
	@echo "    test-ci        Run tests for CI (with XML coverage)"
	@echo ""
	@echo "  Code Quality:"
	@echo "    lint           Run ruff linter"
	@echo "    lint-fix       Run ruff linter with auto-fix"
	@echo "    format         Format code with black"
	@echo "    format-check   Check code formatting without changes"
	@echo "    type-check     Run mypy type checker"
	@echo "    quality        Run all quality checks (lint, format-check, type-check)"
	@echo ""
	@echo "  Database:"
	@echo "    migrate        Run database migrations"
	@echo "    migration      Create a new migration (use: make migration msg='message')"
	@echo ""
	@echo "  Docker:"
	@echo "    docker-build   Build Docker image"
	@echo "    docker-run     Run Docker container"
	@echo ""
	@echo "  Utilities:"
	@echo "    clean          Clean up generated files"
	@echo "    run            Run the development server"

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

# Testing
test:
	pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html

test-cov:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=xml --cov-report=term-missing

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

test-ci:
	pytest tests/ -v --cov=src --cov-report=xml --cov-report=term --cov-fail-under=80

# Code Quality
lint:
	ruff check .

lint-fix:
	ruff check . --fix

format:
	black .

format-check:
	black --check .

type-check:
	mypy src/

quality: lint format-check type-check

# Database
migrate:
	alembic upgrade head

migration:
	@read -p "Migration message: " MSG; \
	alembic revision --autogenerate -m "$$MSG"

# Docker
docker-build:
	docker build -t specterdefence:latest .

docker-run:
	docker run -p 8000:8000 --env-file .env specterdefence:latest

# Run development server
run:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Clean up
clean:
	rm -rf __pycache__ */__pycache__ */*/__pycache__ */*/*/__pycache__
	rm -rf .pytest_cache .coverage htmlcov coverage.xml
	rm -rf build/ dist/ *.egg-info
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name ".DS_Store" -delete
