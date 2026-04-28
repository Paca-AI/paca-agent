"""Pull listener — polls the platform API at a configurable interval."""

from __future__ import annotations

import asyncio

from paca_agent.listeners.base import BaseListener
from paca_agent.models import Task
from paca_agent.utils.logging import get_logger

logger = get_logger(__name__)


class PullListener(BaseListener):
    """Polls the platform every *interval* seconds for new assignments."""

    async def start(self) -> None:
        interval = self._settings.listener.pull_interval
        ai_user = self._settings.ai_account_id
        logger.info("pull_listener.start", interval=interval, ai_account_id=ai_user)

        # Track tasks we've already dispatched to avoid duplicates
        seen: set[str] = set()

        while True:
            try:
                tasks: list[Task] = await self._platform.get_assigned_tasks(ai_user)
                new_tasks = [t for t in tasks if t.id not in seen]

                for task in new_tasks:
                    seen.add(task.id)
                    logger.info("pull_listener.new_task", task_id=task.id, title=task.title)
                    await self._dispatcher.dispatch(task)

            except Exception as exc:
                logger.error("pull_listener.poll_error", error=str(exc))

            await asyncio.sleep(interval)
