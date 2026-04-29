"""Tests for configuration loading."""

from __future__ import annotations

import pytest

from paca_agent.config import GitHubSettings, LLMSettings, PlatformSettings, PlatformType


def test_github_settings_valid_repo() -> None:
    settings = GitHubSettings(token="tok", repo="owner/repo")  # type: ignore[call-arg]
    assert settings.repo == "owner/repo"


def test_github_settings_invalid_repo() -> None:
    with pytest.raises(ValueError, match="owner/repo"):
        GitHubSettings(token="tok", repo="invalid-no-slash")  # type: ignore[call-arg]


def test_platform_settings_strips_trailing_slash() -> None:
    s = PlatformSettings(  # type: ignore[call-arg]
        PLATFORM=PlatformType.PACA,
        base_url="https://api.paca.dev/",
        api_key="key",
    )
    assert not s.base_url.endswith("/")


def test_llm_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_MODEL", raising=False)
    # Pass _env_file=None so the real .env doesn't override the coded default
    s = LLMSettings(api_key="key", _env_file=None)  # type: ignore[call-arg]
    assert "claude" in s.model
