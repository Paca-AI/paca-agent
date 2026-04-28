"""Abstract base class for all project management platform integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from paca_agent.models import Task


class BasePlatform(ABC):
    """Contract that every platform adapter must fulfil."""

    def __init__(self, base_url: str, api_key: str, **kwargs: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "BasePlatform":
        self._client = self._build_client()
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _build_client(self) -> httpx.AsyncClient:
        """Return a pre-configured :class:`httpx.AsyncClient`."""
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._auth_headers(),
            timeout=30.0,
        )

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Platform client is not open. Use `async with platform:`")
        return self._client

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def _auth_headers(self) -> dict[str, str]:
        """Return HTTP headers required to authenticate with the platform."""

    @abstractmethod
    async def get_assigned_tasks(self, user_id: str) -> list[Task]:
        """Return all tasks currently assigned to *user_id*."""

    @abstractmethod
    async def update_task_status(self, task_id: str, status: str) -> None:
        """Change the status of a task."""

    @abstractmethod
    async def add_task_comment(self, task_id: str, comment: str) -> None:
        """Post a comment on a task."""

    # ------------------------------------------------------------------
    # Status helpers — override per-platform if names differ
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def status_in_progress(self) -> str:
        """Platform-specific name for the 'In Progress' status."""

    @property
    @abstractmethod
    def status_ready_for_review(self) -> str:
        """Platform-specific name for the 'Ready for Review' status."""

    @property
    @abstractmethod
    def status_done(self) -> str:
        """Platform-specific name for the 'Done' status."""

    # ------------------------------------------------------------------
    # Optional: MCP configuration
    # ------------------------------------------------------------------

    def mcp_config(self) -> dict | None:
        """Return an MCP server config dict for this platform, or *None*."""
        return None
