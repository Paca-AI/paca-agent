"""Tests for push listener webhook parsing."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from paca_agent.listeners.push import PushListener, _infer_type
from paca_agent.models import TaskType


@pytest.fixture()
def listener(settings) -> PushListener:
    platform = MagicMock()
    dispatcher = AsyncMock()
    return PushListener(settings=settings, platform=platform, dispatcher=dispatcher)


def test_infer_type_code() -> None:
    assert _infer_type("Please implement the login feature") == TaskType.CODE


def test_infer_type_general() -> None:
    assert _infer_type("Write the quarterly report") == TaskType.GENERAL


def test_parse_paca_webhook_assignment(listener: PushListener) -> None:
    payload = {
        "event": "task.assigned",
        "task": {
            "id": "99",
            "title": "Fix bug",
            "description": "Fix the login bug",
            "status": {"name": "todo"},
            "assignee": {"id": "ai-bot"},
        },
    }
    task = listener._parse_paca(payload)
    assert task is not None
    assert task.id == "99"


def test_parse_paca_webhook_wrong_assignee(listener: PushListener) -> None:
    payload = {
        "event": "task.assigned",
        "task": {
            "id": "99",
            "title": "Fix bug",
            "description": "",
            "status": {"name": "todo"},
            "assignee": {"id": "other-user"},
        },
    }
    task = listener._parse_paca(payload)
    assert task is None


def test_parse_jira_webhook(listener: PushListener) -> None:
    payload = {
        "webhookEvent": "jira:issue_assigned",
        "issue": {
            "key": "PROJ-5",
            "fields": {
                "summary": "Implement feature",
                "description": "Implement the OAuth flow",
                "status": {"name": "To Do"},
                "assignee": {"accountId": "ai-bot"},
            },
        },
    }
    task = listener._parse_jira(payload)
    assert task is not None
    assert task.id == "PROJ-5"
    assert task.task_type == TaskType.CODE


def test_parse_unknown_platform_returns_none(listener: PushListener) -> None:
    task = listener._parse_webhook("unknown_platform", {})
    assert task is None
