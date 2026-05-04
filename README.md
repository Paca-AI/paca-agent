# paca-agent

> An AI agent that automatically handles task assignments across popular project management platforms — powered by the [OpenHands SDK](https://docs.openhands.dev/sdk).

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Overview

**paca-agent** connects your project management platform to an AI agent. When a task is assigned to the designated AI account, the agent:

1. **Picks up the task** via polling or webhook
2. **Updates the status** to *In Progress*
3. **Completes the work** — for code tasks it clones the repo, implements the solution, and opens a pull request via GitHub MCP
4. **Updates the status** to *Ready for Review* (or *Done* for non-code tasks)

All code execution happens inside an isolated Docker container so your host machine stays clean.

## Supported Platforms & Agent Modes

The agent integrates with task management platforms via REST API polling or webhooks, and supports multiple agent modes representing different roles in the software development lifecycle.

> **Note:** Currently only the **developer** mode is implemented, and only for **Jira**. Support for other modes and platforms is planned for future releases.

| Platform | Developer | Planner | Business Analyst | Tester |
|----------|-----------|---------|-----------------|--------|
| [Jira](https://www.atlassian.com/software/jira) | ✅ | ⏳ | ⏳ | ⏳ |
| [ClickUp](https://clickup.com) | ⏳ | ⏳ | ⏳ | ⏳ |
| [Paca](https://paca.dev) | ⏳ | ⏳ | ⏳ | ⏳ |
| [Trello](https://trello.com) | ⏳ | ⏳ | ⏳ | ⏳ |
| [Redmine](https://www.redmine.org) | ⏳ | ⏳ | ⏳ | ⏳ |

**Agent modes:**
- **Developer** — clones the repo, implements the solution, and opens a pull request
- **Planner** — breaks down tasks and creates sub-tasks
- **Business Analyst** — analyses requirements and refines task descriptions
- **Tester** — validates completed work, performs manual QA, and reports bugs

### Platform MCP Setup

**Jira** — uses the [`sooperset/mcp-atlassian`](https://github.com/sooperset/mcp-atlassian) MCP server via `uvx`, not Atlassian’s Remote MCP Server URL. Configure the Jira connection in `.env` with `JIRA_URL`, `JIRA_USERNAME`, and `JIRA_API_TOKEN` so the adapter can authenticate against your Jira instance using the same settings as the implementation.

> MCP setup for other platforms (ClickUp, Paca, Trello, Redmine) will be documented as support is added.

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

### MCP Servers

The agent always connects the built-in **GitHub MCP** server and any platform-specific MCP server. You can inject additional MCP servers by creating an `mcp.json` file in the same directory you run the agent from — the format is identical to Claude Desktop and VS Code:

```json
{
  "mcpServers": {
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "your-brave-api-key"
      }
    }
  }
}
```

Copy [`mcp.example.json`](mcp.example.json) as a starting point. Set `MCP_CONFIG_FILE` in `.env` to use a different path, or leave it empty to disable file-based MCP loading.

> `mcp.json` is listed in `.gitignore` because it may contain API keys. Commit `mcp.example.json` instead.

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
