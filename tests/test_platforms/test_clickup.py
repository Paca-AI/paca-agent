"""Tests for ClickUp platform adapter."""

from __future__ import annotations

import pytest

from paca_agent.platforms.clickup import ClickUpPlatform


@pytest.fixture()
def platform() -> ClickUpPlatform:
    return ClickUpPlatform(
        base_url="https://api.clickup.com",
        api_key="pk_test_token",
    )


def test_mcp_config(platform: ClickUpPlatform) -> None:
    config = platform.mcp_config()
    assert config is not None
    server = config["mcpServers"]["clickup"]
    assert server["url"] == "https://mcp.clickup.com/mcp"


def test_mcp_prompt_section_code_workflow(platform: ClickUpPlatform) -> None:
    section = platform.mcp_prompt_section("code")
    assert "clickup" in section.lower()
    assert "pull request" in section.lower()
    assert "in progress" in section.lower()
    assert "Platform MCP Actions" in section


def test_mcp_prompt_section_platform_workflow(platform: ClickUpPlatform) -> None:
    section = platform.mcp_prompt_section("platform")
    assert "clickup" in section.lower()
    assert "in progress" in section.lower()
    assert "Platform MCP Actions" in section
