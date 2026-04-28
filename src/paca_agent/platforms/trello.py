"""Trello platform integration.

API docs: https://developer.atlassian.com/cloud/trello/rest/
"""

from __future__ import annotations

from paca_agent.models import Task, TaskType
from paca_agent.platforms.base import BasePlatform


class TrelloPlatform(BasePlatform):
    """Adapter for Trello.

    Trello uses an API key + token pair rather than a single bearer token.
    Pass the combined ``<key>/<token>`` string as *api_key*.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        **kwargs: str,
    ) -> None:
        super().__init__(base_url or "https://api.trello.com", api_key, **kwargs)
        # api_key expected format: "<trello_key>/<trello_token>"
        parts = api_key.split("/", 1)
        self._trello_key = parts[0]
        self._trello_token = parts[1] if len(parts) > 1 else ""

    # ------------------------------------------------------------------
    # Auth — Trello uses query-string params, not a header
    # ------------------------------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        return {"Accept": "application/json"}

    def _auth_params(self) -> dict[str, str]:
        return {"key": self._trello_key, "token": self._trello_token}

    def _build_client(self):  # type: ignore[override]
        import httpx
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._auth_headers(),
            params=self._auth_params(),
            timeout=30.0,
        )

    # ------------------------------------------------------------------
    # Task retrieval
    # ------------------------------------------------------------------

    async def get_assigned_tasks(self, user_id: str) -> list[Task]:
        response = await self.client.get(f"/1/members/{user_id}/cards")
        response.raise_for_status()
        cards = response.json()

        tasks: list[Task] = []
        for card in cards:
            tasks.append(self._parse_card(card))
        return tasks

    def _parse_card(self, card: dict) -> Task:
        description = card.get("desc", "") or ""
        task_type = (
            TaskType.CODE
            if any(kw in description.lower() for kw in ("implement", "fix", "bug", "code"))
            else TaskType.GENERAL
        )
        return Task(
            id=card["id"],
            title=card.get("name", ""),
            description=description,
            status=card.get("idList", ""),
            assignee_id=",".join(card.get("idMembers", [])),
            platform="trello",
            task_type=task_type,
            raw=card,
        )

    # ------------------------------------------------------------------
    # Task mutations
    # ------------------------------------------------------------------

    async def update_task_status(self, task_id: str, status: str) -> None:
        """Move the card to a list with the given name or ID."""
        response = await self.client.put(
            f"/1/cards/{task_id}",
            params={"idList": status},
        )
        response.raise_for_status()

    async def add_task_comment(self, task_id: str, comment: str) -> None:
        response = await self.client.post(
            f"/1/cards/{task_id}/actions/comments",
            params={"text": comment},
        )
        response.raise_for_status()

    # ------------------------------------------------------------------
    # Status names — Trello uses list IDs; override in your .env / subclass
    # ------------------------------------------------------------------

    @property
    def status_in_progress(self) -> str:
        return "In Progress"

    @property
    def status_ready_for_review(self) -> str:
        return "Review"

    @property
    def status_done(self) -> str:
        return "Done"
