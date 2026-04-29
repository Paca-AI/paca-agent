"""Application configuration loaded from environment variables / .env file."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class PlatformType(StrEnum):
    PACA = "paca"
    JIRA = "jira"
    TRELLO = "trello"
    CLICKUP = "clickup"
    REDMINE = "redmine"


class ListenMode(StrEnum):
    PULL = "pull"
    PUSH = "push"


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LLM_", env_file=".env", extra="ignore")

    model: str = "anthropic/claude-sonnet-4-5-20250929"
    api_key: SecretStr = Field(..., description="API key for the LLM provider")
    base_url: str | None = None


class PlatformSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PLATFORM_", env_file=".env", extra="ignore")

    type: PlatformType = Field(default=PlatformType.PACA, alias="PLATFORM")
    base_url: str = Field(..., description="Base URL of the project management platform")
    api_key: SecretStr = Field(..., description="API key / personal access token")
    email: str | None = Field(default=None, description="Account email (Jira, ClickUp)")
    username: str | None = Field(default=None, description="Username (Redmine, Paca)")

    model_config = SettingsConfigDict(
        env_prefix="PLATFORM_",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("base_url")
    @classmethod
    def strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")


class ListenerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    listen_mode: ListenMode = ListenMode.PULL
    pull_interval: int = Field(default=300, ge=10, description="Polling interval in seconds")
    webhook_host: str = "0.0.0.0"
    webhook_port: int = Field(default=8000, ge=1, le=65535)
    webhook_secret: SecretStr | None = None


class GitHubSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GITHUB_", env_file=".env", extra="ignore")

    token: SecretStr = Field(..., description="GitHub personal access token")
    repo: str = Field(..., description="Target repo in owner/repo format")
    default_branch: str = "main"

    @field_validator("repo")
    @classmethod
    def validate_repo_format(cls, v: str) -> str:
        if "/" not in v or len(v.split("/")) != 2:
            raise ValueError("GITHUB_REPO must be in 'owner/repo' format")
        return v


class DockerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DOCKER_", env_file=".env", extra="ignore")

    image: str = "ubuntu:22.04"
    memory: str = "4g"
    cpu_count: int = Field(default=2, ge=1)


class Settings(BaseModel):
    """Top-level settings aggregator. Use :meth:`load` to construct from env."""

    # Nested settings groups
    llm: LLMSettings = Field(default_factory=LLMSettings)
    platform: PlatformSettings = Field(default_factory=PlatformSettings)  # type: ignore[call-arg]
    listener: ListenerSettings = Field(default_factory=ListenerSettings)
    github: GitHubSettings = Field(default_factory=GitHubSettings)  # type: ignore[call-arg]
    docker: DockerSettings = Field(default_factory=DockerSettings)

    # The AI account to watch for new task assignments
    ai_account_id: str = Field(..., description="User ID of the AI account on the platform")

    @classmethod
    def load(cls) -> Settings:
        """Load settings from .env and environment variables."""

        # Use a thin BaseSettings just to read top-level scalars from .env
        class _TopLevel(BaseSettings):
            model_config = SettingsConfigDict(env_file=".env", extra="ignore")
            ai_account_id: str = Field(..., description="User ID of the AI account")

        top = _TopLevel()
        return cls(
            llm=LLMSettings(),
            platform=PlatformSettings(),  # type: ignore[call-arg]
            listener=ListenerSettings(),
            github=GitHubSettings(),  # type: ignore[call-arg]
            docker=DockerSettings(),
            ai_account_id=top.ai_account_id,
        )
