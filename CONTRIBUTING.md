# Contributing to paca-agent

Thank you for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/paca-dev/paca-agent.git
cd paca-agent

# Install all dependencies including dev extras
uv sync --extra dev

# Install pre-commit hooks
uv run pre-commit install
```

## Running Tests

```bash
uv run pytest
```

## Code Style

This project uses [Ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Lint
uv run ruff check src tests

# Format
uv run ruff format src tests
```

## Adding a New Platform

1. Create `src/paca_agent/platforms/<platform>.py`
2. Subclass `BasePlatform` and implement all abstract methods
3. Register the platform in `src/paca_agent/platforms/__init__.py`
4. Add the platform name to `PlatformType` in `src/paca_agent/config.py`
5. Add tests in `tests/test_platforms/test_<platform>.py`
6. Update `README.md`

## Pull Request Guidelines

- Keep PRs focused on a single change
- Add tests for new functionality
- Update documentation as needed
- Make sure CI passes before requesting review
