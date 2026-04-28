"""Tests for Paca platform adapter."""

from __future__ import annotations

import pytest
import respx
import httpx

from paca_agent.platforms.paca import PacaPlatform


@pytest.fixture()
def platform() -> PacaPlatform:
    return PacaPlatform(base_url="https://api.paca.dev", api_key="test-key")


@respx.mock
async def test_get_assigned_tasks(platform: PacaPlatform) -> None:
    respx.get("https://api.paca.dev/v1/tasks").mock(
        return_value=httpx.Response(
            200,
            json={
                "tasks": [
                    {
                        "id": "42",
                        "title": "Fix login bug",
                        "description": "Implement a fix for the login bug.",
                        "status": {"name": "todo"},
                        "assignee": {"id": "ai-bot"},
                    }
                ]
            },
        )
    )

    async with platform:
        tasks = await platform.get_assigned_tasks("ai-bot")

    assert len(tasks) == 1
    assert tasks[0].id == "42"
    assert tasks[0].platform == "paca"


@respx.mock
async def test_update_task_status(platform: PacaPlatform) -> None:
    respx.patch("https://api.paca.dev/v1/tasks/42").mock(
        return_value=httpx.Response(200, json={})
    )

    async with platform:
        await platform.update_task_status("42", "in_progress")


@respx.mock
async def test_add_task_comment(platform: PacaPlatform) -> None:
    respx.post("https://api.paca.dev/v1/tasks/42/comments").mock(
        return_value=httpx.Response(201, json={})
    )

    async with platform:
        await platform.add_task_comment("42", "AI started working on this.")
