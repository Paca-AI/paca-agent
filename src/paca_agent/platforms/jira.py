"""Jira platform integration.

Uses the Jira REST API v3.
API docs: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
"""

from __future__ import annotations

import base64

from paca_agent.models import Task, TaskType
from paca_agent.platforms.base import BasePlatform


class JiraPlatform(BasePlatform):
    """Adapter for Jira Cloud / Jira Data Center."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        email: str | None = None,
        **kwargs: str,
    ) -> None:
        super().__init__(base_url, api_key, **kwargs)
        self.email = email

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        if self.email:
            credentials = base64.b64encode(f"{self.email}:{self._api_key}".encode()).decode()
            auth = f"Basic {credentials}"
        else:
            auth = f"Bearer {self._api_key}"
        return {
            "Authorization": auth,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ------------------------------------------------------------------
    # Task retrieval
    # ------------------------------------------------------------------

    async def get_assigned_tasks(self, user_id: str) -> list[Task]:
        jql = f'assignee = "{user_id}" AND statusCategory != Done ORDER BY created DESC'
        response = await self.client.get(
            "/rest/api/3/search",
            params={"jql": jql, "maxResults": 50},
        )
        response.raise_for_status()
        data = response.json()

        tasks: list[Task] = []
        for issue in data.get("issues", []):
            tasks.append(self._parse_issue(issue))
        return tasks

    def _parse_issue(self, issue: dict) -> Task:
        fields = issue.get("fields", {})
        description_doc = fields.get("description") or {}
        description = self._extract_text(description_doc)
        task_type = (
            TaskType.CODE
            if any(kw in description.lower() for kw in ("implement", "fix", "refactor", "bug"))
            else TaskType.GENERAL
        )
        return Task(
            id=issue["key"],
            title=fields.get("summary", ""),
            description=description,
            status=fields.get("status", {}).get("name", ""),
            assignee_id=str(fields.get("assignee", {}).get("accountId", "")),
            platform="jira",
            task_type=task_type,
            raw=issue,
        )

    @staticmethod
    def _extract_text(adf_node: dict) -> str:
        """Recursively extract plain text from Atlassian Document Format."""
        if not isinstance(adf_node, dict):
            return ""
        if adf_node.get("type") == "text":
            return adf_node.get("text", "")
        parts = [JiraPlatform._extract_text(child) for child in adf_node.get("content", [])]
        return " ".join(p for p in parts if p)

    # ------------------------------------------------------------------
    # Task mutations
    # ------------------------------------------------------------------

    async def update_task_status(self, task_id: str, status: str) -> None:
        """Transition a Jira issue to the given status name."""
        # First fetch available transitions
        tr_resp = await self.client.get(f"/rest/api/3/issue/{task_id}/transitions")
        tr_resp.raise_for_status()
        transitions = tr_resp.json().get("transitions", [])

        target = next(
            (t for t in transitions if t["name"].lower() == status.lower()),
            None,
        )
        if target is None:
            raise ValueError(
                f"Transition '{status}' not found for issue {task_id}. "
                f"Available: {[t['name'] for t in transitions]}"
            )

        resp = await self.client.post(
            f"/rest/api/3/issue/{task_id}/transitions",
            json={"transition": {"id": target["id"]}},
        )
        resp.raise_for_status()

    async def add_task_comment(self, task_id: str, comment: str) -> None:
        response = await self.client.post(
            f"/rest/api/3/issue/{task_id}/comment",
            json={
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": comment}]}
                    ],
                }
            },
        )
        response.raise_for_status()

    # ------------------------------------------------------------------
    # Status names (Jira default workflow)
    # ------------------------------------------------------------------

    @property
    def status_in_progress(self) -> str:
        return "In Progress"

    @property
    def status_ready_for_review(self) -> str:
        return "In Review"

    @property
    def status_done(self) -> str:
        return "Done"
