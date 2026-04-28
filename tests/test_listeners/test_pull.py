"""Tests for pull listener."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from paca_agent.listeners.pull import PullListener
from paca_agent.models import Task, TaskType


@pytest.fixture()
def dispatcher() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def platform(code_task: Task) -> MagicMock:
    mock = MagicMock()
    mock.get_assigned_tasks = AsyncMock(return_value=[code_task])
    return mock


async def test_pull_listener_dispatches_new_task(settings, platform, dispatcher, code_task) -> None:
    settings.listener.pull_interval = 0  # no sleep in tests
    listener = PullListener(settings=settings, platform=platform, dispatcher=dispatcher)

    # Run one iteration only
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        mock_sleep.side_effect = asyncio.CancelledError()
        with pytest.raises(asyncio.CancelledError):
            await listener.start()

    dispatcher.dispatch.assert_awaited_once_with(code_task)


async def test_pull_listener_skips_seen_tasks(settings, platform, dispatcher, code_task) -> None:
    settings.listener.pull_interval = 0
    listener = PullListener(settings=settings, platform=platform, dispatcher=dispatcher)

    # Simulate two iterations
    call_count = 0

    async def fake_sleep(_: float) -> None:
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError()

    with patch("asyncio.sleep", side_effect=fake_sleep):
        with pytest.raises(asyncio.CancelledError):
            await listener.start()

    # Despite two polls returning the same task, dispatch called only once
    assert dispatcher.dispatch.call_count == 1
