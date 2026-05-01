"""Jira platform integration.

Uses the Jira REST API v3.
API docs: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
"""

from __future__ import annotations

import base64

from paca_agent.models import Task
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
        response = await self.client.post(
            "/rest/api/3/search/jql",
            json={
                "jql": jql,
                "maxResults": 50,
                "fields": ["summary", "description", "status", "assignee", "issuetype", "priority"],
            },
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
        return Task(
            id=issue.get("key") or issue.get("id", ""),
            title=fields.get("summary", ""),
            description=description,
            status=fields.get("status", {}).get("name", ""),
            assignee_id=str(fields.get("assignee", {}).get("accountId", "")),
            platform="jira",
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

    async def get_available_statuses(self, task_id: str) -> list[str]:
        """Return the names of all transitions available for the given Jira issue."""
        resp = await self.client.get(f"/rest/api/3/issue/{task_id}/transitions")
        resp.raise_for_status()
        return [t["name"] for t in resp.json().get("transitions", [])]

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

    async def assign_task(self, task_id: str, user_id: str) -> None:
        response = await self.client.put(
            f"/rest/api/3/issue/{task_id}/assignee",
            json={"accountId": user_id},
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

    # ------------------------------------------------------------------
    # MCP configuration — sooperset/mcp-atlassian
    # https://github.com/sooperset/mcp-atlassian
    # ------------------------------------------------------------------

    def mcp_config(self) -> dict | None:
        env: dict[str, str] = {
            "JIRA_URL": self.base_url,
        }
        if self.email:
            env["JIRA_USERNAME"] = self.email
            env["JIRA_API_TOKEN"] = self._api_key
        else:
            env["JIRA_PERSONAL_TOKEN"] = self._api_key

        return {
            "mcpServers": {
                "mcp-atlassian": {
                    "command": "uvx",
                    "args": ["mcp-atlassian"],
                    "env": env,
                }
            }
        }

    def mcp_prompt_section(self, workflow: str) -> str:
        if workflow == "code":
            instructions = (
                "The **mcp-atlassian** server is available to you.\n"
                "Before you start coding:\n"
                "1. Use `mcp-atlassian` tools (e.g. `jira_transition_issue`) to transition "
                'the Jira issue to an appropriate "in progress" status.\n'
                "After creating the pull request:\n"
                "2. Transition the issue to the appropriate review status (e.g. *In Review*).\n"
                "3. Add a comment on the issue with the pull request URL and a short summary "
                "using `jira_add_comment`."
            )
        else:
            instructions = (
                "The **mcp-atlassian** server is available to you.\n"
                "Before you start working:\n"
                "- Use `mcp-atlassian` tools (e.g. `jira_transition_issue`) to transition "
                'the issue to an appropriate "in progress" status.\n'
                "Use its tools to interact with the Jira project:\n"
                "- Create or update sub-tasks, bugs, and epics as required.\n"
                "- Add comments to communicate findings or decisions.\n"
                "When your work is done:\n"
                "- Transition the issue to the most appropriate final status and add a summary comment."
            )
        return f"""
## Platform MCP Actions
{instructions}
"""
