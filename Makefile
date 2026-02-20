.PHONY: install dev lint run clean help

PYTHON ?= python3
VENV := .venv
BIN := $(VENV)/bin

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: $(VENV)/pyvenv.cfg ## Install production dependencies

$(VENV)/pyvenv.cfg: pyproject.toml
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -e .
	@touch $@

dev: $(VENV)/pyvenv.cfg ## Install dev dependencies
	$(BIN)/pip install -e ".[dev]"

lint: ## Run ruff linter
	$(BIN)/ruff check src/
	$(BIN)/ruff format --check src/

format: ## Auto-format code
	$(BIN)/ruff format src/
	$(BIN)/ruff check --fix src/

run: $(VENV)/pyvenv.cfg ## Run with default settings (past week)
	$(BIN)/gh-weekly-updates $(ARGS)

run-verbose: $(VENV)/pyvenv.cfg ## Run with verbose logging
	$(BIN)/gh-weekly-updates --verbose $(ARGS)

test: dev ## Run tests
	$(BIN)/pytest tests/ -v

clean: ## Remove venv and build artifacts
	rm -rf $(VENV) build/ dist/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
