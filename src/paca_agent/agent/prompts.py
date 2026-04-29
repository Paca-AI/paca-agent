"""Prompt builders for the OpenHands agent."""

from __future__ import annotations

from paca_agent.models import Task


def build_task_prompt(
    task: Task,
    github_repo: str,
    default_branch: str,
    credential_helper_path: str = "",
    committer_name: str = "paca-agent",
    committer_email: str = "paca-agent@users.noreply.github.com",
    available_statuses: list[str] | None = None,
) -> str:
    """Build the agent's instruction prompt for the given *task*."""
    branch_name = _branch_name(task)
    clone_url_https = f"https://github.com/{github_repo}.git"
    clone_url_ssh = f"git@github.com:{github_repo}.git"
    credential_setup = _credential_setup_step(credential_helper_path)
    status_section = _status_section(available_statuses or [])
    return f"""You are an AI agent. Complete the following task from the project management system.

## Task
**ID**: {task.id}
**Title**: {task.title}
**Platform**: {task.platform}

## Description
{task.description}
{status_section}
## Instructions
1. Configure git authentication: {credential_setup}
2. Analyse the task and determine what needs to be done.
3. Clone the repository using HTTPS: `git clone {clone_url_https}`
   - If the HTTPS clone fails (e.g. "Repository not found" or authentication error), immediately retry using SSH: `git clone {clone_url_ssh}`
   - Do NOT search for the repository, fork it, or create a new one — just switch to SSH and continue.
4. Create a new branch named `{branch_name}` from `{default_branch}`.
5. Before making any commits, configure git to use the correct author identity:
   - `git config user.name "{committer_name}"`
   - `git config user.email "{committer_email}"`
6. Complete the task: if it involves code changes, implement them following the existing code style; otherwise commit any relevant output, notes, or deliverables to the branch.
7. Commit your work with a descriptive commit message referencing the task ID `{task.id}`.
8. Push the branch and open a pull request targeting `{default_branch}`.
   - PR title: `[{task.id}] {task.title}`
   - PR body: include a summary of what was done and reference the task ID.
9. Once the PR is created, call the `report_pr` tool with the PR URL so the system can record it.
10. Call the `set_status` tool with the status that best means "ready for review" from the available statuses list above.

Do NOT modify unrelated files. Do NOT leave the branch unpushed.
"""


def _credential_setup_step(helper_path: str) -> str:
    """Return the inline instruction the agent should run to configure git credentials."""
    if helper_path:
        return (
            "`export GIT_CONFIG_COUNT=1; "
            "export GIT_CONFIG_KEY_0=credential.helper; "
            f"export GIT_CONFIG_VALUE_0='{helper_path}'`"
        )
    # No credentials — public repo or credentials already configured externally.
    return "(no credentials needed — repository is public or pre-configured)"


def _status_section(available_statuses: list[str]) -> str:
    """Return a formatted prompt section listing available statuses, or empty string."""
    if not available_statuses:
        return ""
    lines = "\n".join(f"  - {s}" for s in available_statuses)
    return f"""
## Available Task Statuses
Choose the most appropriate status when calling the `set_status` tool:
{lines}

"""


def _branch_name(task: Task) -> str:
    """Generate a clean git branch name from the task."""
    slug = task.title.lower()
    # Replace non-alphanumeric chars with hyphens
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")[:50]
    return f"ai/{task.id}/{slug}"
