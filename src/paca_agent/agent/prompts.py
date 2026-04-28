"""Prompt builders for the OpenHands agent."""

from __future__ import annotations

from paca_agent.models import Task, TaskType


def build_task_prompt(task: Task, github_repo: str, default_branch: str) -> str:
    """Build the agent's instruction prompt for the given *task*."""
    if task.task_type == TaskType.CODE:
        return _code_task_prompt(task, github_repo, default_branch)
    return _general_task_prompt(task)


def _code_task_prompt(task: Task, github_repo: str, default_branch: str) -> str:
    branch_name = _branch_name(task)
    return f"""You are an AI software engineer. Complete the following task from the project management system.

## Task
**ID**: {task.id}
**Title**: {task.title}
**Platform**: {task.platform}

## Description
{task.description}

## Instructions
1. Use the GitHub MCP tool to clone or check out the repository `{github_repo}`.
2. Create a new feature branch named `{branch_name}` from `{default_branch}`.
3. Implement the required changes. Write clean, well-tested code following the existing code style.
4. Commit your changes with a descriptive commit message referencing the task ID `{task.id}`.
5. Push the branch and open a pull request targeting `{default_branch}`.
   - PR title: `[{task.id}] {task.title}`
   - PR body: include a summary of what was changed and reference the task ID.
6. Once the PR is created, respond with "PR_CREATED: <pr_url>" so the system can capture the URL.

Do NOT modify unrelated files. Do NOT leave the branch unpushed.
"""


def _general_task_prompt(task: Task) -> str:
    return f"""You are an AI assistant. Complete the following task.

## Task
**ID**: {task.id}
**Title**: {task.title}
**Platform**: {task.platform}

## Description
{task.description}

## Instructions
Analyse the task and complete it to the best of your ability.
When finished, summarise what you did in 2-3 sentences so the result can be recorded.
"""


def _branch_name(task: Task) -> str:
    """Generate a clean git branch name from the task."""
    slug = task.title.lower()
    # Replace non-alphanumeric chars with hyphens
    import re
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")[:50]
    return f"ai/{task.id}/{slug}"
