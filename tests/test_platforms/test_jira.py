"""Tests for Jira platform adapter."""

from __future__ import annotations

import httpx
import pytest
import respx

from paca_agent.platforms.jira import JiraPlatform


@pytest.fixture()
def platform() -> JiraPlatform:
    return JiraPlatform(
        base_url="https://myorg.atlassian.net",
        api_key="api-token",
        email="user@example.com",
    )


@respx.mock
async def test_get_assigned_tasks(platform: JiraPlatform) -> None:
    respx.get("https://myorg.atlassian.net/rest/api/3/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "issues": [
                    {
                        "key": "PROJ-1",
                        "fields": {
                            "summary": "Fix auth bug",
                            "description": None,
                            "status": {"name": "To Do"},
                            "assignee": {"accountId": "ai-bot"},
                        },
                    }
                ]
            },
        )
    )

    async with platform:
        tasks = await platform.get_assigned_tasks("ai-bot")

    assert len(tasks) == 1
    assert tasks[0].id == "PROJ-1"
    assert tasks[0].platform == "jira"


@respx.mock
async def test_update_task_status(platform: JiraPlatform) -> None:
    respx.get("https://myorg.atlassian.net/rest/api/3/issue/PROJ-1/transitions").mock(
        return_value=httpx.Response(
            200,
            json={"transitions": [{"id": "21", "name": "In Progress"}]},
        )
    )
    respx.post("https://myorg.atlassian.net/rest/api/3/issue/PROJ-1/transitions").mock(
        return_value=httpx.Response(204)
    )

    async with platform:
        await platform.update_task_status("PROJ-1", "In Progress")


def test_extract_text_from_adf() -> None:
    adf = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Hello"}, {"type": "text", "text": "World"}],
            }
        ],
    }
    result = JiraPlatform._extract_text(adf)
    assert "Hello" in result
    assert "World" in result
