"""Prompt builders for the OpenHands agent."""

from __future__ import annotations

import re

from paca_agent.models import Task

_DEFAULT_AGENT_INTRO = (
    "You are an AI agent. Complete the following task from the project management system."
)


def build_code_task_prompt(
    task: Task,
    github_repo: str,
    default_branch: str,
    credential_helper_path: str = "",
    committer_name: str = "paca-agent",
    committer_email: str = "280579135+paca-agent@users.noreply.github.com",
    available_statuses: list[str] | None = None,
    agent_system_prompt: str = "",
    mcp_prompt_section: str = "",
) -> str:
    """Build the prompt for *code* workflow agents (clone -> implement -> commit -> PR).

    *agent_system_prompt* is the body of the selected agent mode's Markdown
    file.  When provided it replaces the default one-line intro so the agent
    adopts the persona and principles defined in the mode file.

    *mcp_prompt_section* is the platform-specific MCP usage guidance string,
    obtained from ``BasePlatform.mcp_prompt_section()``.
    """
    intro = agent_system_prompt.strip() if agent_system_prompt.strip() else _DEFAULT_AGENT_INTRO
    branch_name = _branch_name(task)
    clone_url_https = f"https://github.com/{github_repo}.git"
    clone_url_ssh = f"git@github.com:{github_repo}.git"
    credential_setup = _credential_setup_step(credential_helper_path)
    status_section = _status_section(available_statuses or [])
    body = _render(
        intro,
        {
            "task_id": task.id,
            "task_title": task.title,
            "branch_name": branch_name,
            "clone_url_https": clone_url_https,
            "clone_url_ssh": clone_url_ssh,
            "credential_setup": credential_setup,
            "default_branch": default_branch,
            "committer_name": committer_name,
            "committer_email": committer_email,
        },
    )
    return f"""{body}

## Task
**ID**: {task.id}
**Title**: {task.title}
**Platform**: {task.platform}

## Description
{task.description}
{status_section}{mcp_prompt_section}"""


def build_platform_task_prompt(
    task: Task,
    available_statuses: list[str] | None = None,
    agent_system_prompt: str = "",
    mcp_prompt_section: str = "",
) -> str:
    """Build the prompt for *platform* workflow agents.

    These agents analyse the task and act via the project-management platform's
    MCP tools (creating sub-tasks, bugs, comments, etc.).  They do NOT clone
    any repository or open pull requests.

    *agent_system_prompt* is the body of the selected agent mode's Markdown file.

    *mcp_prompt_section* is the platform-specific MCP usage guidance string,
    obtained from ``BasePlatform.mcp_prompt_section()``.
    """
    intro = agent_system_prompt.strip() if agent_system_prompt.strip() else _DEFAULT_AGENT_INTRO
    status_section = _status_section(available_statuses or [])
    body = _render(intro, {"task_id": task.id, "task_title": task.title})
    return f"""{body}

## Task
**ID**: {task.id}
**Title**: {task.title}
**Platform**: {task.platform}

## Description
{task.description}
{status_section}{mcp_prompt_section}"""


def build_task_prompt(
    task: Task,
    github_repo: str = "",
    default_branch: str = "main",
    credential_helper_path: str = "",
    committer_name: str = "paca-agent",
    committer_email: str = "280579135+paca-agent@users.noreply.github.com",
    available_statuses: list[str] | None = None,
    agent_system_prompt: str = "",
    workflow: str = "code",
    mcp_prompt_section: str = "",
) -> str:
    """Route to the correct prompt builder based on *workflow*.

    *mcp_prompt_section* is the platform-specific MCP usage guidance string,
    obtained from ``BasePlatform.mcp_prompt_section()``.
    """
    if workflow == "platform":
        return build_platform_task_prompt(
            task=task,
            available_statuses=available_statuses,
            agent_system_prompt=agent_system_prompt,
            mcp_prompt_section=mcp_prompt_section,
        )
    return build_code_task_prompt(
        task=task,
        github_repo=github_repo,
        default_branch=default_branch,
        credential_helper_path=credential_helper_path,
        committer_name=committer_name,
        committer_email=committer_email,
        available_statuses=available_statuses,
        agent_system_prompt=agent_system_prompt,
        mcp_prompt_section=mcp_prompt_section,
    )


def _render(template: str, variables: dict[str, str]) -> str:
    """Substitute {placeholder} variables in *template*, leaving unknown placeholders intact."""

    class _SafeDict(dict):  # type: ignore[type-arg]
        def __missing__(self, key: str) -> str:
            return f"{{{key}}}"

    return template.format_map(_SafeDict(variables))


def _credential_setup_step(helper_path: str) -> str:
    """Return the inline instruction the agent should run to configure git credentials."""
    if helper_path:
        return (
            "`export GIT_CONFIG_COUNT=1; "
            "export GIT_CONFIG_KEY_0=credential.helper; "
            f"export GIT_CONFIG_VALUE_0='{helper_path}'`"
        )
    return "(no credentials needed — repository is public or pre-configured)"


def _status_section(available_statuses: list[str]) -> str:
    """Return a formatted prompt section listing available statuses, or empty string."""
    if not available_statuses:
        return ""
    lines = "\n".join(f"  - {s}" for s in available_statuses)
    return f"""
## Available Task Statuses
The following statuses are available on this task. Use the platform MCP tools to:
- Set the task to an appropriate "in progress" status BEFORE you start working.
- Set the most appropriate final status when your work is done.
{lines}

"""


def _branch_name(task: Task) -> str:
    """Generate a clean git branch name from the task."""
    slug = task.title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")[:50]
    return f"ai/{task.id}/{slug}"
