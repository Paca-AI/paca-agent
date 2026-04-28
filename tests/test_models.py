"""Tests for domain models."""

from __future__ import annotations

from paca_agent.models import Task, TaskType


def test_task_short_description_truncates() -> None:
    long_desc = "x" * 200
    task = Task(
        id="1",
        title="test",
        description=long_desc,
        status="todo",
        assignee_id="ai",
        platform="paca",
    )
    assert len(task.short_description()) <= 123  # 120 chars + ellipsis


def test_task_short_description_unchanged_when_short() -> None:
    task = Task(
        id="1",
        title="test",
        description="Short.",
        status="todo",
        assignee_id="ai",
        platform="paca",
    )
    assert task.short_description() == "Short."


def test_task_default_type_is_general() -> None:
    task = Task(id="1", title="t", description="d", status="s", assignee_id="a", platform="p")
    assert task.task_type == TaskType.GENERAL
