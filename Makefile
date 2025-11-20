# Makefile for Autotube development

.PHONY: help install install-dev test test-cov lint format clean run build pre-commit

# Default target
help:
	@echo "Autotube Development Commands:"
	@echo ""
	@echo "Setup:"
	@echo "  make install        Install production dependencies"
	@echo "  make install-dev    Install all dependencies (including dev tools)"
	@echo "  make pre-commit     Install pre-commit hooks"
	@echo ""
	@echo "Development:"
	@echo "  make run            Run the application"
	@echo "  make format         Format code with Black and isort"
	@echo "  make lint           Run linters (flake8, ruff, mypy)"
	@echo "  make test           Run tests"
	@echo "  make test-cov       Run tests with coverage report"
	@echo ""
	@echo "Build & Distribution:"
	@echo "  make build          Build executable with PyInstaller"
	@echo "  make clean          Remove build artifacts and cache files"
	@echo ""
	@echo "CI/CD:"
	@echo "  make ci             Run all CI checks (format, lint, test)"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

pre-commit:
	pre-commit install

# Testing
test:
	pytest

test-cov:
	pytest --cov=src --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

test-watch:
	pytest-watch

# Code Quality
format:
	black src tests
	isort src tests
	@echo "Code formatted successfully!"

lint:
	@echo "Running flake8..."
	flake8 src tests
	@echo "Running ruff..."
	ruff check src tests
	@echo "Running mypy..."
	mypy src
	@echo "All linters passed!"

lint-fix:
	ruff check --fix src tests
	black src tests
	isort src tests

# Security
security:
	@echo "Running Bandit security check..."
	bandit -r src
	@echo "Running Safety dependency check..."
	safety check -r requirements.txt

# Development
run:
	python src/main.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage dist build
	@echo "Cleaned up build artifacts and cache files!"

# Build
build:
	@echo "Building executable with PyInstaller..."
	pyinstaller --name Autotube \
		--windowed \
		--onefile \
		--add-data "src:src" \
		src/main.py
	@echo "Build complete! Check dist/ directory"

# CI/CD
ci: lint test
	@echo "All CI checks passed!"

# Documentation
docs:
	mkdocs build
	@echo "Documentation built in site/ directory"

docs-serve:
	mkdocs serve

# Complete setup for new developers
setup: install-dev pre-commit
	@echo ""
	@echo "✅ Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Run 'make test' to verify tests pass"
	@echo "  2. Run 'make run' to start the application"
	@echo "  3. See 'make help' for more commands"
