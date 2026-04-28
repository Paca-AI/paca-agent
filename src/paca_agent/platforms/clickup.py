"""ClickUp platform integration.

API docs: https://clickup.com/api
"""

from __future__ import annotations

from paca_agent.models import Task, TaskType
from paca_agent.platforms.base import BasePlatform


class ClickUpPlatform(BasePlatform):
    """Adapter for ClickUp."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        **kwargs: str,
    ) -> None:
        super().__init__(base_url or "https://api.clickup.com", api_key, **kwargs)

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": self._api_key,
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Task retrieval
    # ------------------------------------------------------------------

    async def get_assigned_tasks(self, user_id: str) -> list[Task]:
        response = await self.client.get(
            "/api/v2/task",
            params={"assignees[]": user_id, "statuses[]": "to do"},
        )
        response.raise_for_status()
        data = response.json()

        tasks: list[Task] = []
        for task in data.get("tasks", []):
            tasks.append(self._parse_task(task))
        return tasks

    def _parse_task(self, item: dict) -> Task:
        description = item.get("description", "") or ""
        task_type = (
            TaskType.CODE
            if any(kw in description.lower() for kw in ("implement", "fix", "bug", "code"))
            else TaskType.GENERAL
        )
        assignees = item.get("assignees", [])
        assignee_id = ",".join(str(a.get("id", "")) for a in assignees)
        return Task(
            id=item["id"],
            title=item.get("name", ""),
            description=description,
            status=item.get("status", {}).get("status", ""),
            assignee_id=assignee_id,
            platform="clickup",
            task_type=task_type,
            raw=item,
        )

    # ------------------------------------------------------------------
    # Task mutations
    # ------------------------------------------------------------------

    async def update_task_status(self, task_id: str, status: str) -> None:
        response = await self.client.put(
            f"/api/v2/task/{task_id}",
            json={"status": status},
        )
        response.raise_for_status()

    async def add_task_comment(self, task_id: str, comment: str) -> None:
        response = await self.client.post(
            f"/api/v2/task/{task_id}/comment",
            json={"comment_text": comment, "notify_all": False},
        )
        response.raise_for_status()

    # ------------------------------------------------------------------
    # Status names
    # ------------------------------------------------------------------

    @property
    def status_in_progress(self) -> str:
        return "in progress"

    @property
    def status_ready_for_review(self) -> str:
        return "review"

    @property
    def status_done(self) -> str:
        return "complete"
