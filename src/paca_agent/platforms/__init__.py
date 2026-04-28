"""Platform registry and factory."""

from __future__ import annotations

from paca_agent.config import PlatformSettings, PlatformType
from paca_agent.platforms.base import BasePlatform
from paca_agent.platforms.clickup import ClickUpPlatform
from paca_agent.platforms.jira import JiraPlatform
from paca_agent.platforms.paca import PacaPlatform
from paca_agent.platforms.redmine import RedminePlatform
from paca_agent.platforms.trello import TrelloPlatform

__all__ = [
    "BasePlatform",
    "PacaPlatform",
    "JiraPlatform",
    "TrelloPlatform",
    "ClickUpPlatform",
    "RedminePlatform",
    "build_platform",
]


def build_platform(settings: PlatformSettings) -> BasePlatform:
    """Instantiate the correct :class:`BasePlatform` from *settings*."""
    api_key = settings.api_key.get_secret_value()
    kwargs: dict[str, str] = {}

    if settings.email:
        kwargs["email"] = settings.email
    if settings.username:
        kwargs["username"] = settings.username

    match settings.type:
        case PlatformType.PACA:
            return PacaPlatform(settings.base_url, api_key, **kwargs)
        case PlatformType.JIRA:
            return JiraPlatform(settings.base_url, api_key, **kwargs)
        case PlatformType.TRELLO:
            return TrelloPlatform(settings.base_url, api_key, **kwargs)
        case PlatformType.CLICKUP:
            return ClickUpPlatform(settings.base_url, api_key, **kwargs)
        case PlatformType.REDMINE:
            return RedminePlatform(settings.base_url, api_key, **kwargs)
        case _:
            raise ValueError(f"Unsupported platform: {settings.type!r}")
