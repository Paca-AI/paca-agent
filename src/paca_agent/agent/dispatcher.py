"""Task dispatcher — orchestrates agent execution."""

from __future__ import annotations

from paca_agent.agent.runner import AgentRunner, RunResult
from paca_agent.config import Settings
from paca_agent.models import Task
from paca_agent.platforms.base import BasePlatform
from paca_agent.utils.logging import get_logger

logger = get_logger(__name__)


class TaskDispatcher:
    """Coordinate a single task through its full lifecycle."""

    def __init__(self, settings: Settings, platform: BasePlatform) -> None:
        self._platform = platform
        self._runner = AgentRunner(
            llm_settings=settings.llm,
            github_settings=settings.github,
            docker_settings=settings.docker,
            agent_mode=settings.agent_mode,
        )

    async def dispatch(self, task: Task) -> None:
        logger.info("dispatch.start", task_id=task.id, title=task.title)

        await self._comment(task, "🤖 AI agent picked up this task and is working on it.")

        result: RunResult = await self._runner.run(task, self._platform)

        if not result.success:
            logger.warning("dispatch.agent_failed", task_id=task.id, error=result.error)
            await self._comment(
                task,
                f"❌ AI agent encountered an error:\n\n```\n{result.error}\n```\n\n"
                "Please review and re-assign or handle manually.",
            )

        logger.info("dispatch.done", task_id=task.id, success=result.success)

    async def _comment(self, task: Task, message: str) -> None:
        try:
            await self._platform.add_task_comment(task.id, message)
        except Exception as exc:
            logger.warning("dispatch.comment_failed", task_id=task.id, error=str(exc))
