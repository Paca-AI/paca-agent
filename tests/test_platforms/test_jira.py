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
    respx.post("https://myorg.atlassian.net/rest/api/3/search/jql").mock(
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


@respx.mock
async def test_get_available_statuses(platform: JiraPlatform) -> None:
    respx.get("https://myorg.atlassian.net/rest/api/3/issue/PROJ-1/transitions").mock(
        return_value=httpx.Response(
            200,
            json={
                "transitions": [
                    {"id": "11", "name": "Ready to review"},
                    {"id": "21", "name": "In Progress"},
                    {"id": "31", "name": "Done"},
                ]
            },
        )
    )

    async with platform:
        statuses = await platform.get_available_statuses("PROJ-1")

    assert statuses == ["Ready to review", "In Progress", "Done"]


def test_mcp_config_with_email(platform: JiraPlatform) -> None:
    config = platform.mcp_config()
    assert config is not None
    server = config["mcpServers"]["mcp-atlassian"]
    assert server["command"] == "uvx"
    assert server["args"] == ["mcp-atlassian"]
    env = server["env"]
    assert env["JIRA_URL"] == "https://myorg.atlassian.net"
    assert env["JIRA_USERNAME"] == "user@example.com"
    assert env["JIRA_API_TOKEN"] == "api-token"


def test_mcp_config_personal_token_when_no_email() -> None:
    platform_no_email = JiraPlatform(
        base_url="https://myorg.atlassian.net",
        api_key="my-token",
    )
    config = platform_no_email.mcp_config()
    assert config is not None
    env = config["mcpServers"]["mcp-atlassian"]["env"]
    assert env["JIRA_PERSONAL_TOKEN"] == "my-token"
    assert "JIRA_USERNAME" not in env


def test_mcp_prompt_section_code_workflow(platform: JiraPlatform) -> None:
    section = platform.mcp_prompt_section("code")
    assert "mcp-atlassian" in section.lower()
    assert "jira_transition_issue" in section.lower()
    assert "pull request" in section.lower()
    assert "in progress" in section.lower()
    assert "Platform MCP Actions" in section


def test_mcp_prompt_section_platform_workflow(platform: JiraPlatform) -> None:
    section = platform.mcp_prompt_section("platform")
    assert "mcp-atlassian" in section.lower()
    assert "in progress" in section.lower()
    assert "Platform MCP Actions" in section
