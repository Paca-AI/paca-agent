"""Shared test fixtures and helpers."""

from __future__ import annotations

import pytest

from paca_agent.config import (
    DockerSettings,
    GitHubSettings,
    ListenerSettings,
    LLMSettings,
    PlatformSettings,
    PlatformType,
    Settings,
)
from paca_agent.models import Task, TaskType


@pytest.fixture()
def llm_settings() -> LLMSettings:
    return LLMSettings(model="openai/gpt-4o-mini", api_key="test-key")  # type: ignore[call-arg]


@pytest.fixture()
def github_settings() -> GitHubSettings:
    return GitHubSettings(token="test-token", repo="owner/repo")  # type: ignore[call-arg]


@pytest.fixture()
def docker_settings() -> DockerSettings:
    return DockerSettings()


@pytest.fixture()
def platform_settings() -> PlatformSettings:
    return PlatformSettings(  # type: ignore[call-arg]
        PLATFORM=PlatformType.PACA,
        base_url="https://api.paca.dev",
        api_key="test-platform-key",
    )


@pytest.fixture()
def listener_settings() -> ListenerSettings:
    return ListenerSettings()


@pytest.fixture()
def settings(
    llm_settings: LLMSettings,
    platform_settings: PlatformSettings,
    listener_settings: ListenerSettings,
    github_settings: GitHubSettings,
    docker_settings: DockerSettings,
) -> Settings:
    return Settings(  # type: ignore[call-arg]
        llm=llm_settings,
        platform=platform_settings,
        listener=listener_settings,
        github=github_settings,
        docker=docker_settings,
        ai_account_id="ai-bot",
    )


@pytest.fixture()
def code_task() -> Task:
    return Task(
        id="TASK-1",
        title="Fix login bug",
        description="Implement a fix for the login bug where users can't log in with OAuth.",
        status="todo",
        assignee_id="ai-bot",
        platform="paca",
        task_type=TaskType.CODE,
    )


@pytest.fixture()
def general_task() -> Task:
    return Task(
        id="TASK-2",
        title="Write project documentation",
        description="Write the README and API documentation for the new service.",
        status="todo",
        assignee_id="ai-bot",
        platform="paca",
        task_type=TaskType.GENERAL,
    )
