"""Tests for agent prompt generation."""

from __future__ import annotations

from paca_agent.agent.prompts import (
    _branch_name,
    _render,
    build_platform_task_prompt,
    build_task_prompt,
)
from paca_agent.models import Task


def test_code_task_prompt_contains_branch(code_task: Task) -> None:
    agent_prompt = "Clone: {clone_url_https} — branch {branch_name} from {default_branch}"
    prompt = build_task_prompt(code_task, "owner/repo", "main", agent_system_prompt=agent_prompt)
    assert "ai/TASK-1/" in prompt
    assert "owner/repo" in prompt
    assert "main" in prompt


def test_general_task_prompt_creates_pr(general_task: Task) -> None:
    agent_prompt = (
        "Clone the repo: git clone {clone_url_https}\n"
        "Open a pull request targeting {default_branch}.\n"
    )
    prompt = build_task_prompt(general_task, "owner/repo", "main", agent_system_prompt=agent_prompt)
    assert "pull request" in prompt.lower()
    assert "clone" in prompt.lower()


def test_branch_name_sanitises_title() -> None:
    task = Task(
        id="T-99",
        title="Fix: Auth/Login Bug!!",
        description="",
        status="",
        assignee_id="",
        platform="paca",
    )
    branch = _branch_name(task)
    assert branch.startswith("ai/T-99/")
    assert "!" not in branch
    assert "/" not in branch.split("T-99/", 1)[1]


def test_template_vars_substituted_in_agent_prompt(code_task: Task) -> None:
    agent_prompt = "Repo: {clone_url_https} | Branch: {branch_name} | Task: {task_id}"
    prompt = build_task_prompt(code_task, "owner/repo", "main", agent_system_prompt=agent_prompt)
    assert "https://github.com/owner/repo.git" in prompt
    assert "ai/TASK-1/" in prompt
    assert "TASK-1" in prompt


def test_render_leaves_unknown_placeholders_intact() -> None:
    result = _render("Hello {name}, your score is {score}.", {"name": "Alice"})
    assert result == "Hello Alice, your score is {score}."


def test_agent_system_prompt_replaces_default_intro(code_task: Task) -> None:
    custom_intro = "You are an expert QA engineer focused on test coverage."
    prompt = build_task_prompt(code_task, "owner/repo", "main", agent_system_prompt=custom_intro)
    assert custom_intro in prompt
    assert "You are an AI agent." not in prompt


def test_default_intro_used_when_no_agent_system_prompt(code_task: Task) -> None:
    prompt = build_task_prompt(code_task, "owner/repo", "main")
    assert "You are an AI agent" in prompt


def test_empty_agent_system_prompt_falls_back_to_default(code_task: Task) -> None:
    prompt = build_task_prompt(code_task, "owner/repo", "main", agent_system_prompt="   ")
    assert "You are an AI agent" in prompt


# ---------------------------------------------------------------------------
# Platform workflow
# ---------------------------------------------------------------------------


def test_platform_workflow_has_no_git_instructions(code_task: Task) -> None:
    prompt = build_task_prompt(code_task, workflow="platform")
    assert "git clone" not in prompt
    assert "open a pull request" not in prompt.lower()


def test_platform_workflow_instructs_platform_tools(code_task: Task) -> None:
    agent_prompt = "Use the platform MCP tools to create tasks."
    prompt = build_task_prompt(code_task, workflow="platform", agent_system_prompt=agent_prompt)
    assert "platform MCP tools" in prompt
    assert "git clone" not in prompt


def test_platform_workflow_contains_task_details(code_task: Task) -> None:
    prompt = build_task_prompt(code_task, workflow="platform")
    assert code_task.id in prompt
    assert code_task.title in prompt


def test_build_platform_task_prompt_directly(code_task: Task) -> None:
    prompt = build_platform_task_prompt(
        task=code_task,
        available_statuses=["done", "in-review"],
        agent_system_prompt="You are a planner.",
    )
    assert "You are a planner." in prompt
    assert "done" in prompt
    assert "in-review" in prompt
    assert "git clone" not in prompt


# ---------------------------------------------------------------------------
# MCP prompt section passed through from platform
# ---------------------------------------------------------------------------

_JIRA_CODE_SECTION = (
    "\n## Platform MCP Actions\n"
    "The **mcp-atlassian** server is available to you.\n"
    "Before you start coding:\n"
    "1. Use `mcp-atlassian` tools (e.g. `jira_transition_issue`) to transition "
    'the Jira issue to an appropriate "in progress" status.\n'
    "After creating the pull request:\n"
    "2. Transition the issue to the appropriate review status (e.g. *In Review*).\n"
    "3. Add a comment on the issue with the pull request URL and a short summary "
    "using `jira_add_comment`.\n"
)

_CLICKUP_PLATFORM_SECTION = (
    "\n## Platform MCP Actions\n"
    "The **ClickUp MCP server** (`clickup`) is available to you.\n"
    "Before you start working:\n"
    "- Use `clickup` MCP tools to update the task to an appropriate "
    '"in progress" status.\n'
    "Use its tools to interact with the ClickUp workspace:\n"
    "- Create or update tasks, subtasks, and checklists as required.\n"
    "- Add comments to communicate findings or decisions.\n"
    "When your work is done:\n"
    "- Update the task to the most appropriate final status and add a summary comment.\n"
)


def test_code_prompt_includes_mcp_prompt_section() -> None:
    task = Task(
        id="PROJ-1",
        title="Fix bug",
        description="desc",
        status="todo",
        assignee_id="ai",
        platform="jira",
    )
    prompt = build_task_prompt(
        task,
        github_repo="owner/repo",
        default_branch="main",
        mcp_prompt_section=_JIRA_CODE_SECTION,
    )
    assert "mcp-atlassian" in prompt.lower()
    assert "Platform MCP Actions" in prompt
    assert "pull request" in prompt.lower()
    assert "in progress" in prompt.lower()


def test_platform_prompt_includes_mcp_prompt_section() -> None:
    task = Task(
        id="abc123",
        title="Plan sprint",
        description="desc",
        status="todo",
        assignee_id="ai",
        platform="clickup",
    )
    prompt = build_task_prompt(
        task,
        workflow="platform",
        mcp_prompt_section=_CLICKUP_PLATFORM_SECTION,
    )
    assert "clickup" in prompt.lower()
    assert "Platform MCP Actions" in prompt
    assert "in progress" in prompt.lower()


def test_empty_mcp_prompt_section_omits_section(code_task: Task) -> None:
    prompt = build_task_prompt(code_task, "owner/repo", "main", mcp_prompt_section="")
    assert "Platform MCP Actions" not in prompt


# ---------------------------------------------------------------------------
# Status section
# ---------------------------------------------------------------------------


def test_status_section_includes_in_progress_instruction(code_task: Task) -> None:
    prompt = build_task_prompt(
        code_task, "owner/repo", "main", available_statuses=["todo", "in progress", "done"]
    )
    assert "todo" in prompt
    assert "in progress" in prompt
    assert "done" in prompt
    assert "set_status" not in prompt
    assert "before you start" in prompt.lower() or "before starting" in prompt.lower()
