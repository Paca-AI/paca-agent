"""Tests for TaskDispatcher."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from paca_agent.agent.dispatcher import TaskDispatcher
from paca_agent.agent.runner import RunResult
from paca_agent.models import Task, TaskType


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_task() -> Task:
    return Task(
        id="TASK-1",
        title="Fix login bug",
        description="Implement a fix",
        status="todo",
        assignee_id="ai-bot",
        platform="paca",
        task_type=TaskType.CODE,
    )


def _make_platform(
    status_in_progress: str = "in_progress",
    status_ready_for_review: str = "ready_for_review",
    status_done: str = "done",
) -> MagicMock:
    platform = MagicMock()
    platform.status_in_progress = status_in_progress
    platform.status_ready_for_review = status_ready_for_review
    platform.status_done = status_done
    platform.update_task_status = AsyncMock()
    platform.add_task_comment = AsyncMock()
    platform.assign_task = AsyncMock()
    return platform


def _make_dispatcher(settings, platform) -> TaskDispatcher:
    dispatcher = TaskDispatcher(settings=settings, platform=platform)
    return dispatcher


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_success_with_pr_uses_agent_status(settings) -> None:
    """Agent-supplied status is used when set_status was called."""
    platform = _make_platform()
    dispatcher = _make_dispatcher(settings, platform)
    task = _make_task()
    result = RunResult(
        success=True,
        pr_url="https://github.com/owner/repo/pull/1",
        status="review",
        summary="All done.",
    )

    with patch.object(dispatcher._runner, "run", new=AsyncMock(return_value=result)):
        await dispatcher.dispatch(task)

    platform.update_task_status.assert_any_call(task.id, "review")
    # Confirm the PR URL appears in the comment
    call_args = platform.add_task_comment.call_args_list
    pr_comment = next(
        (str(c) for c in call_args if "pull/1" in str(c)),
        None,
    )
    assert pr_comment is not None


@pytest.mark.asyncio
async def test_dispatch_success_with_pr_falls_back_to_platform_status(settings) -> None:
    """Platform status_ready_for_review is used when the agent did not call set_status."""
    platform = _make_platform()
    dispatcher = _make_dispatcher(settings, platform)
    task = _make_task()
    result = RunResult(
        success=True,
        pr_url="https://github.com/owner/repo/pull/2",
        status=None,  # agent did not call set_status
        summary="",
    )

    with patch.object(dispatcher._runner, "run", new=AsyncMock(return_value=result)):
        await dispatcher.dispatch(task)

    platform.update_task_status.assert_any_call(task.id, "ready_for_review")


@pytest.mark.asyncio
async def test_dispatch_success_with_pr_and_reviewer(settings) -> None:
    """When reviewer_id is set and reassignment succeeds, the comment says so."""
    platform = _make_platform()
    # Override the fixture settings to include a reviewer
    settings_with_reviewer = MagicMock()
    settings_with_reviewer.llm = settings.llm
    settings_with_reviewer.github = settings.github
    settings_with_reviewer.docker = settings.docker
    settings_with_reviewer.reviewer_id = "reviewer-42"

    dispatcher = _make_dispatcher(settings_with_reviewer, platform)
    task = _make_task()
    result = RunResult(
        success=True,
        pr_url="https://github.com/owner/repo/pull/3",
        status="review",
        summary="",
    )

    with patch.object(dispatcher._runner, "run", new=AsyncMock(return_value=result)):
        await dispatcher.dispatch(task)

    platform.assign_task.assert_called_once_with(task.id, "reviewer-42")
    comment_text = " ".join(str(c) for c in platform.add_task_comment.call_args_list)
    assert "reviewer-42" in comment_text


@pytest.mark.asyncio
async def test_dispatch_success_with_pr_reassignment_failure_omits_reviewer_text(settings) -> None:
    """When reassignment fails, the 'Assigned to reviewer' line must NOT appear in the comment."""
    platform = _make_platform()
    platform.assign_task = AsyncMock(side_effect=RuntimeError("API error"))

    settings_with_reviewer = MagicMock()
    settings_with_reviewer.llm = settings.llm
    settings_with_reviewer.github = settings.github
    settings_with_reviewer.docker = settings.docker
    settings_with_reviewer.reviewer_id = "reviewer-99"

    dispatcher = _make_dispatcher(settings_with_reviewer, platform)
    task = _make_task()
    result = RunResult(
        success=True,
        pr_url="https://github.com/owner/repo/pull/4",
        status="review",
        summary="",
    )

    with patch.object(dispatcher._runner, "run", new=AsyncMock(return_value=result)):
        await dispatcher.dispatch(task)

    comment_text = " ".join(str(c) for c in platform.add_task_comment.call_args_list)
    assert "Assigned to reviewer" not in comment_text


@pytest.mark.asyncio
async def test_dispatch_success_without_pr_uses_agent_status(settings) -> None:
    """When no PR URL is present, the agent's status is used (or falls back to status_done)."""
    platform = _make_platform()
    dispatcher = _make_dispatcher(settings, platform)
    task = _make_task()
    result = RunResult(success=True, pr_url=None, status="done", summary="Completed.")

    with patch.object(dispatcher._runner, "run", new=AsyncMock(return_value=result)):
        await dispatcher.dispatch(task)

    platform.update_task_status.assert_any_call(task.id, "done")


@pytest.mark.asyncio
async def test_dispatch_success_without_pr_falls_back_to_platform_done(settings) -> None:
    """Platform status_done is used when there is no PR and no agent status."""
    platform = _make_platform()
    dispatcher = _make_dispatcher(settings, platform)
    task = _make_task()
    result = RunResult(success=True, pr_url=None, status=None, summary="")

    with patch.object(dispatcher._runner, "run", new=AsyncMock(return_value=result)):
        await dispatcher.dispatch(task)

    platform.update_task_status.assert_any_call(task.id, "done")


@pytest.mark.asyncio
async def test_dispatch_no_reviewer_no_assign_call(settings) -> None:
    """When reviewer_id is None no assign_task call is made."""
    platform = _make_platform()
    dispatcher = _make_dispatcher(settings, platform)  # settings fixture has reviewer_id=None
    task = _make_task()
    result = RunResult(
        success=True,
        pr_url="https://github.com/owner/repo/pull/5",
        status="review",
        summary="",
    )

    with patch.object(dispatcher._runner, "run", new=AsyncMock(return_value=result)):
        await dispatcher.dispatch(task)

    platform.assign_task.assert_not_called()
    comment_text = " ".join(str(c) for c in platform.add_task_comment.call_args_list)
    assert "Assigned to reviewer" not in comment_text


@pytest.mark.asyncio
async def test_dispatch_failure_posts_error_comment(settings) -> None:
    """On agent failure a comment with the error text is posted and no status is set afterward."""
    platform = _make_platform()
    dispatcher = _make_dispatcher(settings, platform)
    task = _make_task()
    result = RunResult(success=False, error="Something went wrong")

    with patch.object(dispatcher._runner, "run", new=AsyncMock(return_value=result)):
        await dispatcher.dispatch(task)

    # Only one status call — the initial "in progress" one
    assert platform.update_task_status.call_count == 1
    platform.update_task_status.assert_called_once_with(task.id, "in_progress")

    comment_text = " ".join(str(c) for c in platform.add_task_comment.call_args_list)
    assert "Something went wrong" in comment_text
