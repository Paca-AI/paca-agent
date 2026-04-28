"""Push listener — receives task assignment webhooks via FastAPI."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
from typing import Annotated

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request, status

from paca_agent.config import PlatformType
from paca_agent.listeners.base import BaseListener
from paca_agent.models import Task, TaskType
from paca_agent.utils.logging import get_logger

logger = get_logger(__name__)


def _build_app(listener: PushListener) -> FastAPI:
    app = FastAPI(title="paca-agent webhook", docs_url=None, redoc_url=None)

    @app.post("/webhook/{platform}", status_code=status.HTTP_202_ACCEPTED)
    async def receive_webhook(
        platform: str,
        request: Request,
        x_hub_signature_256: Annotated[str | None, Header()] = None,
    ) -> dict:
        payload = await request.body()

        # Validate HMAC signature if a secret is configured
        secret = listener._settings.listener.webhook_secret
        if secret:
            if not x_hub_signature_256:
                raise HTTPException(status_code=400, detail="Missing X-Hub-Signature-256 header")
            mac = hmac.new(secret.get_secret_value().encode(), payload, hashlib.sha256)
            expected = "sha256=" + mac.hexdigest()
            if not hmac.compare_digest(expected, x_hub_signature_256):
                raise HTTPException(status_code=401, detail="Invalid webhook signature")

        data = await request.json()
        task = listener._parse_webhook(platform, data)
        if task:
            logger.info("push_listener.new_task", task_id=task.id, platform=platform)
            asyncio.create_task(listener._dispatcher.dispatch(task))

        return {"status": "accepted"}

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app


class PushListener(BaseListener):
    """Listens for incoming webhook POST requests."""

    async def start(self) -> None:
        host = self._settings.listener.webhook_host
        port = self._settings.listener.webhook_port
        logger.info("push_listener.start", host=host, port=port)

        app = _build_app(self)
        config = uvicorn.Config(app, host=host, port=port, log_level="warning")
        server = uvicorn.Server(config)
        await server.serve()

    # ------------------------------------------------------------------
    # Webhook payload parsers — one per platform
    # ------------------------------------------------------------------

    def _parse_webhook(self, platform_str: str, data: dict) -> Task | None:
        try:
            platform_type = PlatformType(platform_str.lower())
        except ValueError:
            logger.warning("push_listener.unknown_platform", platform=platform_str)
            return None

        match platform_type:
            case PlatformType.PACA:
                return self._parse_paca(data)
            case PlatformType.JIRA:
                return self._parse_jira(data)
            case PlatformType.TRELLO:
                return self._parse_trello(data)
            case PlatformType.CLICKUP:
                return self._parse_clickup(data)
            case PlatformType.REDMINE:
                return self._parse_redmine(data)
            case _:
                return None

    def _parse_paca(self, data: dict) -> Task | None:
        event = data.get("event")
        if event not in ("task.assigned", "task.created"):
            return None
        task_data = data.get("task", {})
        assignee = task_data.get("assignee", {})
        if str(assignee.get("id", "")) != str(self._settings.ai_account_id):
            return None
        description = task_data.get("description", "") or ""
        return Task(
            id=str(task_data["id"]),
            title=task_data.get("title", ""),
            description=description,
            status=task_data.get("status", {}).get("name", ""),
            assignee_id=str(assignee.get("id", "")),
            platform="paca",
            task_type=_infer_type(description),
            raw=task_data,
        )

    def _parse_jira(self, data: dict) -> Task | None:
        webhook_event = data.get("webhookEvent", "")
        if "assigned" not in webhook_event and "created" not in webhook_event:
            return None
        issue = data.get("issue", {})
        fields = issue.get("fields", {})
        assignee = fields.get("assignee") or {}
        if str(assignee.get("accountId", "")) != str(self._settings.ai_account_id):
            return None
        description = str(fields.get("description", "") or "")
        return Task(
            id=issue.get("key", ""),
            title=fields.get("summary", ""),
            description=description,
            status=fields.get("status", {}).get("name", ""),
            assignee_id=str(assignee.get("accountId", "")),
            platform="jira",
            task_type=_infer_type(description),
            raw=issue,
        )

    def _parse_trello(self, data: dict) -> Task | None:
        action = data.get("action", {})
        if action.get("type") != "addMemberToCard":
            return None
        member_id = action.get("member", {}).get("id", "")
        if str(member_id) != str(self._settings.ai_account_id):
            return None
        card = action.get("data", {}).get("card", {})
        description = card.get("desc", "") or ""
        return Task(
            id=card.get("id", ""),
            title=card.get("name", ""),
            description=description,
            status=card.get("idList", ""),
            assignee_id=str(member_id),
            platform="trello",
            task_type=_infer_type(description),
            raw=card,
        )

    def _parse_clickup(self, data: dict) -> Task | None:
        event = data.get("event", "")
        if event not in ("taskAssigneeUpdated", "taskCreated"):
            return None
        task_data = data.get("task_id") and data or {}
        assignees = task_data.get("history_items", [{}])[0].get("after", [])
        ai_id = str(self._settings.ai_account_id)
        if not any(str(a.get("id", "")) == ai_id for a in assignees):
            return None
        description = task_data.get("description", "") or ""
        return Task(
            id=str(task_data.get("task_id", "")),
            title=task_data.get("task_name", ""),
            description=description,
            status=task_data.get("task_status", {}).get("status", ""),
            assignee_id=ai_id,
            platform="clickup",
            task_type=_infer_type(description),
            raw=task_data,
        )

    def _parse_redmine(self, data: dict) -> Task | None:
        payload = data.get("payload", {})
        issue = payload.get("issue", {})
        assignee = issue.get("assignee", {})
        if str(assignee.get("id", "")) != str(self._settings.ai_account_id):
            return None
        description = issue.get("description", "") or ""
        return Task(
            id=str(issue.get("id", "")),
            title=issue.get("subject", ""),
            description=description,
            status=issue.get("status", {}).get("name", ""),
            assignee_id=str(assignee.get("id", "")),
            platform="redmine",
            task_type=_infer_type(description),
            raw=issue,
        )


def _infer_type(description: str) -> TaskType:
    """Heuristic: classify as CODE if description contains programming keywords."""
    keywords = ("implement", "fix", "refactor", "bug", "code", "feature", "patch", "pr")
    return TaskType.CODE if any(kw in description.lower() for kw in keywords) else TaskType.GENERAL
