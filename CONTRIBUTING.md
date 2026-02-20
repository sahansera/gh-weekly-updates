# Contributing to gh-weekly-updates

Thanks for your interest in contributing! Here's how to get started.

## Development setup

```bash
# Clone the repo
git clone https://github.com/sahansera/gh-weekly-updates.git
cd gh-weekly-updates

# Create a virtual environment
python -m venv .venv && source .venv/bin/activate

# Install in editable mode with dev dependencies
make dev
```

## Running locally

```bash
# Copy the example config and customise
cp config.example.yaml config.yaml

# Run with defaults (past week, repos from config)
make run

# Run with custom args
make run ARGS="--since 2025-01-01 --until 2025-01-07"
```

## Code style

```bash
make lint     # ruff check
make format   # ruff format
```

## Pull requests

1. Fork the repo and create a feature branch from `main`.
2. Add or update tests if applicable.
3. Run `make lint` and `make format`.
4. Open a PR with a clear description of the change.

## Reporting issues

Open a GitHub issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Python version and OS
