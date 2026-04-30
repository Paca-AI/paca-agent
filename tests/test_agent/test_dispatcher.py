"""Tests for TaskDispatcher."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from paca_agent.agent.dispatcher import TaskDispatcher
from paca_agent.agent.runner import RunResult
from paca_agent.models import Task


def _make_task() -> Task:
    return Task(
        id="TASK-1",
        title="Fix login bug",
        description="Implement a fix",
        status="todo",
        assignee_id="ai-bot",
        platform="jira",
    )


def _make_platform() -> MagicMock:
    platform = MagicMock()
    platform.add_task_comment = AsyncMock()
    return platform


def _make_dispatcher(settings, platform) -> TaskDispatcher:
    return TaskDispatcher(settings=settings, platform=platform)


@pytest.mark.asyncio
async def test_dispatch_success_posts_initial_comment(settings) -> None:
    """On success the dispatcher posts only the initial 'picked up' comment via REST API."""
    platform = _make_platform()
    dispatcher = _make_dispatcher(settings, platform)
    task = _make_task()
    result = RunResult(
        success=True,
        pr_url="https://github.com/owner/repo/pull/99",
        summary="Done.",
    )

    with patch.object(dispatcher._runner, "run", new=AsyncMock(return_value=result)):
        await dispatcher.dispatch(task)

    platform.add_task_comment.assert_called_once()
    call_args = platform.add_task_comment.call_args
    assert "picked up this task" in call_args[0][1]


@pytest.mark.asyncio
async def test_dispatch_failure_posts_initial_and_error_comments(settings) -> None:
    """On agent failure both the initial 'picked up' comment and the error comment are posted."""
    platform = _make_platform()
    dispatcher = _make_dispatcher(settings, platform)
    task = _make_task()
    result = RunResult(success=False, error="Something went wrong")

    with patch.object(dispatcher._runner, "run", new=AsyncMock(return_value=result)):
        await dispatcher.dispatch(task)

    assert platform.add_task_comment.call_count == 2
    call_args_list = platform.add_task_comment.call_args_list
    messages = [str(c) for c in call_args_list]
    assert any("picked up this task" in m for m in messages)
    assert any("Something went wrong" in m for m in messages)


@pytest.mark.asyncio
async def test_dispatch_comment_error_is_non_fatal(settings) -> None:
    """If posting a comment fails, the dispatcher should not raise."""
    platform = _make_platform()
    platform.add_task_comment = AsyncMock(side_effect=RuntimeError("API down"))
    dispatcher = _make_dispatcher(settings, platform)
    task = _make_task()
    result = RunResult(success=False, error="Agent crashed")

    with patch.object(dispatcher._runner, "run", new=AsyncMock(return_value=result)):
        await dispatcher.dispatch(task)  # should not raise
