"""Shared domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Task:
    """A task assigned to the AI agent."""

    id: str
    title: str
    description: str
    status: str
    assignee_id: str
    platform: str

    repo_url: str | None = None
    branch_hint: str | None = None

    # Raw platform-specific payload (for passing context to MCP)
    raw: dict = field(default_factory=dict)

    # Timestamps
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def short_description(self) -> str:
        """Return a truncated description safe for log messages."""
        max_len = 120
        if len(self.description) <= max_len:
            return self.description
        return self.description[:max_len] + "…"
