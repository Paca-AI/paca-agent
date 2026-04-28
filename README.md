# paca-agent

> An AI agent that automatically handles task assignments across popular project management platforms — powered by the [OpenHands SDK](https://docs.openhands.dev/sdk).

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Overview

**paca-agent** connects your project management platform to an AI agent. When a task is assigned to the designated AI account, the agent:

1. **Picks up the task** via polling or webhook
2. **Updates the status** to *In Progress*
3. **Completes the work** — for code tasks it clones the repo, implements the solution, and opens a pull request via GitHub MCP
4. **Updates the status** to *Ready for Review* (or *Done* for non-code tasks)

All code execution happens inside an isolated Docker container so your host machine stays clean.

## Supported Platforms

| Platform | Status |
|----------|--------|
| [Paca](https://paca.dev) | ✅ Supported |
| [Jira](https://www.atlassian.com/software/jira) | ✅ Supported |
| [Trello](https://trello.com) | ✅ Supported |
| [ClickUp](https://clickup.com) | ✅ Supported |
| [Redmine](https://www.redmine.org) | ✅ Supported |

## Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/) ≥ 0.8.13
- Docker (for sandboxed code execution)
- An LLM API key (Anthropic, OpenAI, or [OpenHands Cloud](https://app.openhands.dev))

### Installation

```bash
# Clone the repository
git clone https://github.com/paca-dev/paca-agent.git
cd paca-agent

# Install dependencies
uv sync

# Copy and configure environment variables
cp .env.example .env
```

Edit `.env` with your configuration (see [Configuration](#configuration)).

### Run

```bash
# Pull mode (polls every N seconds)
uv run paca-agent

# Or directly with Python
uv run python -m paca_agent
```

## Configuration

Copy `.env.example` to `.env` and set the variables below.

### Core

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_MODEL` | LLM model name (any [LiteLLM](https://docs.litellm.ai/docs/providers) model) | `anthropic/claude-sonnet-4-5-20250929` |
| `LLM_API_KEY` | API key for the LLM provider | — |
| `LLM_BASE_URL` | Optional custom base URL | — |

### Platform

| Variable | Description |
|----------|-------------|
| `PLATFORM` | One of `paca`, `jira`, `trello`, `clickup`, `redmine` |
| `PLATFORM_BASE_URL` | Base URL of your platform instance |
| `PLATFORM_API_KEY` | API key / token |
| `PLATFORM_EMAIL` | Account email (Jira / ClickUp) |
| `PLATFORM_USERNAME` | Username (Redmine / Paca) |
| `AI_ACCOUNT_ID` | User ID of the AI account to watch for assignments |

### Listening Mode

| Variable | Description | Default |
|----------|-------------|---------|
| `LISTEN_MODE` | `pull` or `push` | `pull` |
| `PULL_INTERVAL` | Polling interval in seconds | `300` |
| `WEBHOOK_HOST` | Host to bind the webhook server | `0.0.0.0` |
| `WEBHOOK_PORT` | Port for the webhook server | `8000` |
| `WEBHOOK_SECRET` | Optional secret for validating webhook payloads | — |

### GitHub

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | Personal access token with repo + PR permissions |
| `GITHUB_REPO` | Target repository in `owner/repo` format |
| `GITHUB_DEFAULT_BRANCH` | Base branch for PRs | `main` |

### Docker Sandbox

| Variable | Description | Default |
|----------|-------------|---------|
| `DOCKER_IMAGE` | Base Docker image for the sandbox | `ubuntu:22.04` |
| `DOCKER_MEMORY` | Memory limit | `4g` |
| `DOCKER_CPU_COUNT` | CPU limit | `2` |

## Webhook Setup (Push Mode)

Set `LISTEN_MODE=push`, then configure your platform to send assignment webhooks to:

```
POST http://<your-host>:<WEBHOOK_PORT>/webhook/<platform>
```

Example for Jira: `POST https://agent.example.com/webhook/jira`

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  paca-agent                      │
│                                                  │
│  ┌──────────┐    ┌──────────────────────────┐   │
│  │ Listener │───▶│     Task Dispatcher       │   │
│  │ pull/push│    └──────────┬───────────────┘   │
│  └──────────┘               │                   │
│                             ▼                   │
│                   ┌─────────────────┐           │
│                   │  Platform Client│           │
│                   │  (update status)│           │
│                   └────────┬────────┘           │
│                            │                   │
│                            ▼                   │
│                   ┌─────────────────┐          │
│                   │  Agent Runner   │          │
│                   │  (OpenHands SDK)│          │
│                   └────────┬────────┘          │
│                            │                  │
│                  ┌─────────┴──────────┐       │
│                  │  Docker Workspace   │       │
│                  │  + GitHub MCP       │       │
│                  │  + Platform MCP     │       │
│                  └────────────────────┘       │
└───────────────────────────────────────────────┘
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). All contributions are welcome!

## License

[Apache-2.0](LICENSE)
