"""Paca platform integration.

API docs: https://docs.paca.dev/api
"""

from __future__ import annotations

from paca_agent.models import Task, TaskType
from paca_agent.platforms.base import BasePlatform


class PacaPlatform(BasePlatform):
    """Adapter for the Paca project management platform."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        username: str | None = None,
        **kwargs: str,
    ) -> None:
        super().__init__(base_url, api_key, **kwargs)
        self.username = username

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ------------------------------------------------------------------
    # Task retrieval
    # ------------------------------------------------------------------

    async def get_assigned_tasks(self, user_id: str) -> list[Task]:
        response = await self.client.get(
            "/v1/tasks",
            params={"assignee": user_id, "status": "todo"},
        )
        response.raise_for_status()
        data = response.json()

        tasks: list[Task] = []
        for item in data.get("tasks", []):
            tasks.append(self._parse_task(item))
        return tasks

    def _parse_task(self, item: dict) -> Task:
        description = item.get("description", "") or ""
        task_type = (
            TaskType.CODE
            if any(kw in description.lower() for kw in ("implement", "fix", "refactor", "code"))
            else TaskType.GENERAL
        )
        return Task(
            id=str(item["id"]),
            title=item.get("title", ""),
            description=description,
            status=item.get("status", {}).get("name", ""),
            assignee_id=str(item.get("assignee", {}).get("id", "")),
            platform="paca",
            task_type=task_type,
            raw=item,
        )

    # ------------------------------------------------------------------
    # Task mutations
    # ------------------------------------------------------------------

    async def update_task_status(self, task_id: str, status: str) -> None:
        response = await self.client.patch(
            f"/v1/tasks/{task_id}",
            json={"status": status},
        )
        response.raise_for_status()

    async def add_task_comment(self, task_id: str, comment: str) -> None:
        response = await self.client.post(
            f"/v1/tasks/{task_id}/comments",
            json={"body": comment},
        )
        response.raise_for_status()

    # ------------------------------------------------------------------
    # Status names
    # ------------------------------------------------------------------

    @property
    def status_in_progress(self) -> str:
        return "in_progress"

    @property
    def status_ready_for_review(self) -> str:
        return "ready_for_review"

    @property
    def status_done(self) -> str:
        return "done"
