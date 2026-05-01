"""ClickUp platform integration.

API docs: https://clickup.com/api
"""

from __future__ import annotations

from paca_agent.models import Task
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
        assignees = item.get("assignees", [])
        assignee_id = ",".join(str(a.get("id", "")) for a in assignees)
        return Task(
            id=item["id"],
            title=item.get("name", ""),
            description=description,
            status=item.get("status", {}).get("status", ""),
            assignee_id=assignee_id,
            platform="clickup",
            raw=item,
        )

    # ------------------------------------------------------------------
    # Task mutations
    # ------------------------------------------------------------------

    async def get_available_statuses(self, task_id: str) -> list[str]:  # noqa: ARG002
        return [self.status_in_progress, self.status_ready_for_review, self.status_done]

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

    async def assign_task(self, task_id: str, user_id: str) -> None:
        response = await self.client.put(
            f"/api/v2/task/{task_id}",
            json={"assignees": {"add": [int(user_id)], "rem": []}},
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

    # ------------------------------------------------------------------
    # MCP configuration — ClickUp Remote MCP Server
    # Docs: https://developer.clickup.com/docs/connect-an-ai-assistant-to-clickups-mcp-server-1
    # Uses OAuth 2.0; the user must complete a one-time browser-based
    # auth flow before running headless. Access tokens are cached by
    # FastMCP at ~/.fastmcp/oauth-mcp-client-cache/.
    # ------------------------------------------------------------------

    def mcp_config(self) -> dict | None:
        return {
            "mcpServers": {
                "clickup": {
                    "url": "https://mcp.clickup.com/mcp",
                    "auth": "oauth",
                }
            }
        }

    def mcp_prompt_section(self, workflow: str) -> str:
        if workflow == "code":
            instructions = (
                "The **ClickUp MCP server** (`clickup`) is available to you.\n"
                "Before you start coding:\n"
                "1. Use `clickup` MCP tools to update the task to an appropriate "
                '"in progress" status.\n'
                "After creating the pull request:\n"
                "2. Update the task status to the appropriate review status (e.g. *review*).\n"
                "3. Add a comment on the task with the pull request URL and a short summary."
            )
        else:
            instructions = (
                "The **ClickUp MCP server** (`clickup`) is available to you.\n"
                "Before you start working:\n"
                "- Use `clickup` MCP tools to update the task to an appropriate "
                '"in progress" status.\n'
                "Use its tools to interact with the ClickUp workspace:\n"
                "- Create or update tasks, subtasks, and checklists as required.\n"
                "- Add comments to communicate findings or decisions.\n"
                "When your work is done:\n"
                "- Update the task to the most appropriate final status and add a summary comment."
            )
        return f"""
## Platform MCP Actions
{instructions}
"""
