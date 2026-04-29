"""Tests for agent prompt generation."""

from __future__ import annotations

from paca_agent.agent.prompts import _branch_name, build_task_prompt
from paca_agent.models import Task


def test_code_task_prompt_contains_branch(code_task: Task) -> None:
    prompt = build_task_prompt(code_task, "owner/repo", "main")
    assert "ai/TASK-1/" in prompt
    assert "owner/repo" in prompt
    assert "main" in prompt


def test_general_task_prompt_creates_pr(general_task: Task) -> None:
    prompt = build_task_prompt(general_task, "owner/repo", "main")
    assert "pull request" in prompt.lower()
    assert "clone" in prompt.lower()
    assert "report_pr" in prompt


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
