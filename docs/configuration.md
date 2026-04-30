# Configuration Reference

## Environment Variables

### LLM

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_MODEL` | Yes | `anthropic/claude-sonnet-4-5-20250929` | Any [LiteLLM-supported model](https://docs.litellm.ai/docs/providers) |
| `LLM_API_KEY` | Yes | — | API key for the model provider |
| `LLM_BASE_URL` | No | — | Custom base URL (e.g. Azure OpenAI, local Ollama) |

### Platform

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PLATFORM` | Yes | `paca` | Platform name: `paca`, `jira`, `trello`, `clickup`, `redmine` |
| `PLATFORM_BASE_URL` | Yes | — | Base URL of the platform API |
| `PLATFORM_API_KEY` | Yes | — | API key or personal access token |
| `PLATFORM_EMAIL` | Jira/ClickUp | — | Account email for Basic Auth |
| `PLATFORM_USERNAME` | Redmine/Paca | — | Account username |
| `AI_ACCOUNT_ID` | Yes | — | User ID / username of the AI account to watch |

### Listening Mode

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LISTEN_MODE` | No | `pull` | `pull` for polling, `push` for webhooks |
| `PULL_INTERVAL` | No | `300` | Seconds between polls (pull mode) |
| `WEBHOOK_HOST` | No | `0.0.0.0` | Bind host for webhook server |
| `WEBHOOK_PORT` | No | `8000` | Port for webhook server |
| `WEBHOOK_SECRET` | No | — | HMAC secret for payload validation |

### GitHub

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_TOKEN` | Yes | — | Personal access token with `repo` + pull_request scopes |
| `GITHUB_REPO` | Yes | — | Repository in `owner/repo` format |
| `GITHUB_DEFAULT_BRANCH` | No | `main` | Base branch for pull requests |

### Docker Sandbox

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DOCKER_IMAGE` | No | `ubuntu:22.04` | Base image for the sandbox container |
| `DOCKER_MEMORY` | No | `4g` | Memory limit |
| `DOCKER_CPU_COUNT` | No | `2` | CPU limit |

### Agent Mode

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AGENT_MODE` | No | `developer` | Name of the agent mode to use (see [Agent Modes](#agent-modes)) |

## Agent Modes

Agent modes define the persona, principles, and behaviour of the AI agent that runs each task.
They are plain Markdown files with a small YAML frontmatter block.

### Built-in Modes

| Mode | Description |
|------|-------------|
| `developer` | Full-stack software developer. Implements features, fixes bugs, writes clean code, opens PRs. |
| `tester` | QA engineer. Writes automated tests, finds edge cases, improves test coverage. |
| `planner` | Technical planner. Breaks down requirements, writes specs and ADRs, produces implementation plans. |
| `business-analyst` | Business analyst. Gathers requirements, writes user stories with acceptance criteria, documents processes. |

### Custom Agent Modes

Create an `agents/` folder in your project root and add a Markdown file for each custom mode:

```
your-project/
└── agents/
    ├── devops.md
    └── security-reviewer.md
```

**File format** (`agents/devops.md`):

```markdown
---
name: devops
description: Infrastructure and DevOps specialist focused on CI/CD and container orchestration.
---

You are an expert DevOps engineer AI agent. Your goal is to improve infrastructure,
automate deployments, and maintain healthy CI/CD pipelines.

## Principles

- Prefer declarative configuration over imperative scripts.
- Every change to infrastructure should be version-controlled and reviewed.
- Fail fast: pipelines should catch issues before they reach production.
```

The frontmatter `name` and `description` fields are optional but recommended.
The body (everything after the second `---`) becomes the system prompt prepended to every task.

User-defined agents in `agents/` take priority over built-in agents with the same name,
allowing you to override the built-in `developer` mode for your project.

## Platform-Specific Notes

### Trello

`PLATFORM_API_KEY` must be in `<key>/<token>` format (both values from [trello.com/app-key](https://trello.com/app-key)).

`update_task_status()` expects a Trello list ID, not a list name.
Use `TRELLO_IN_PROGRESS_LIST_ID` / `TRELLO_REVIEW_LIST_ID` overrides (coming soon) or subclass `TrelloPlatform`.

### Redmine

Status updates use the default Redmine workflow status IDs (2 = In Progress, 3 = Resolved).
Override `_resolve_status_id()` if your Redmine installation uses different IDs.

### Jira

Requires both `PLATFORM_EMAIL` and `PLATFORM_API_KEY` (API token from [id.atlassian.com](https://id.atlassian.com/manage-profile/security/api-tokens)).

Status transitions depend on your project's workflow. The adapter resolves transitions by name (case-insensitive).
