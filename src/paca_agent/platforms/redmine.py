"""Redmine platform integration.

API docs: https://www.redmine.org/projects/redmine/wiki/Rest_api
"""

from __future__ import annotations

from paca_agent.models import Task, TaskType
from paca_agent.platforms.base import BasePlatform

# Redmine default status IDs
_STATUS_IN_PROGRESS = 2
_STATUS_RESOLVED = 3


class RedminePlatform(BasePlatform):
    """Adapter for Redmine."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        **kwargs: str,
    ) -> None:
        super().__init__(base_url, api_key, **kwargs)

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        return {
            "X-Redmine-API-Key": self._api_key,
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Task retrieval
    # ------------------------------------------------------------------

    async def get_assigned_tasks(self, user_id: str) -> list[Task]:
        response = await self.client.get(
            "/issues.json",
            params={"assigned_to_id": user_id, "status_id": "open", "limit": 50},
        )
        response.raise_for_status()
        data = response.json()

        tasks: list[Task] = []
        for issue in data.get("issues", []):
            tasks.append(self._parse_issue(issue))
        return tasks

    def _parse_issue(self, issue: dict) -> Task:
        description = issue.get("description", "") or ""
        task_type = (
            TaskType.CODE
            if any(kw in description.lower() for kw in ("implement", "fix", "bug", "patch"))
            else TaskType.GENERAL
        )
        return Task(
            id=str(issue["id"]),
            title=issue.get("subject", ""),
            description=description,
            status=issue.get("status", {}).get("name", ""),
            assignee_id=str(issue.get("assigned_to", {}).get("id", "")),
            platform="redmine",
            task_type=task_type,
            raw=issue,
        )

    # ------------------------------------------------------------------
    # Task mutations
    # ------------------------------------------------------------------

    async def update_task_status(self, task_id: str, status: str) -> None:
        status_id = self._resolve_status_id(status)
        response = await self.client.put(
            f"/issues/{task_id}.json",
            json={"issue": {"status_id": status_id}},
        )
        response.raise_for_status()

    def _resolve_status_id(self, status_name: str) -> int:
        mapping: dict[str, int] = {
            self.status_in_progress: _STATUS_IN_PROGRESS,
            self.status_ready_for_review: _STATUS_RESOLVED,
            self.status_done: _STATUS_RESOLVED,
        }
        if status_name in mapping:
            return mapping[status_name]
        # If a numeric id was passed directly
        if status_name.isdigit():
            return int(status_name)
        raise ValueError(f"Unknown Redmine status: {status_name!r}")

    async def add_task_comment(self, task_id: str, comment: str) -> None:
        response = await self.client.put(
            f"/issues/{task_id}.json",
            json={"issue": {"notes": comment}},
        )
        response.raise_for_status()

    # ------------------------------------------------------------------
    # Status names
    # ------------------------------------------------------------------

    @property
    def status_in_progress(self) -> str:
        return "In Progress"

    @property
    def status_ready_for_review(self) -> str:
        return "Resolved"

    @property
    def status_done(self) -> str:
        return "Closed"
