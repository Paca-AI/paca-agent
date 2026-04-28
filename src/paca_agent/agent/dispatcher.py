"""Task dispatcher — orchestrates status updates and agent execution."""

from __future__ import annotations

from paca_agent.agent.runner import AgentRunner, RunResult
from paca_agent.config import Settings
from paca_agent.models import Task, TaskType
from paca_agent.platforms.base import BasePlatform
from paca_agent.utils.logging import get_logger

logger = get_logger(__name__)


class TaskDispatcher:
    """Coordinate a single task through its full lifecycle."""

    def __init__(self, settings: Settings, platform: BasePlatform) -> None:
        self._settings = settings
        self._platform = platform
        self._runner = AgentRunner(
            llm_settings=settings.llm,
            github_settings=settings.github,
            docker_settings=settings.docker,
        )

    async def dispatch(self, task: Task) -> None:
        logger.info("dispatch.start", task_id=task.id, title=task.title)

        # 1. Mark as in progress
        await self._set_status(task, self._platform.status_in_progress)
        await self._comment(task, "🤖 AI agent picked up this task and is working on it.")

        # 2. Run the agent
        result: RunResult = await self._runner.run(task, self._platform)

        # 3. Update status based on result
        if result.success:
            if task.task_type == TaskType.CODE and result.pr_url:
                await self._set_status(task, self._platform.status_ready_for_review)
                await self._comment(
                    task,
                    f"✅ AI agent completed the task and opened a pull request:\n{result.pr_url}",
                )
            else:
                await self._set_status(task, self._platform.status_done)
                summary = result.summary or "Task completed."
                await self._comment(task, f"✅ AI agent completed the task.\n\n{summary}")
        else:
            await self._comment(
                task,
                f"❌ AI agent encountered an error:\n\n```\n{result.error}\n```\n\n"
                "Please review and re-assign or handle manually.",
            )

        logger.info("dispatch.done", task_id=task.id, success=result.success)

    # ------------------------------------------------------------------

    async def _set_status(self, task: Task, status: str) -> None:
        try:
            await self._platform.update_task_status(task.id, status)
        except Exception as exc:
            logger.warning("dispatch.status_update_failed", task_id=task.id, error=str(exc))

    async def _comment(self, task: Task, message: str) -> None:
        try:
            await self._platform.add_task_comment(task.id, message)
        except Exception as exc:
            logger.warning("dispatch.comment_failed", task_id=task.id, error=str(exc))
