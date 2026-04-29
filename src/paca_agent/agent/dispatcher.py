"""Task dispatcher — orchestrates status updates and agent execution."""

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
            if result.pr_url:
                # Use the status the agent chose (it saw the real available statuses).
                # Fall back to the platform's hardcoded property when the agent didn't call set_status.
                ready_status = result.status or self._platform.status_ready_for_review
                await self._set_status(task, ready_status)
                reviewer_id = self._settings.reviewer_id
                if reviewer_id:
                    await self._reassign(task, reviewer_id)
                summary = result.summary or ""
                comment = (
                    f"✅ AI agent completed the task and opened a pull request:\n{result.pr_url}"
                )
                if summary:
                    comment += f"\n\n**Summary:**\n{summary}"
                if reviewer_id:
                    comment += f"\n\nAssigned to reviewer `{reviewer_id}` for review."
                await self._comment(task, comment)
            else:
                summary = result.summary or "Task completed."
                done_status = result.status or self._platform.status_done
                await self._set_status(task, done_status)
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

    async def _reassign(self, task: Task, user_id: str) -> None:
        try:
            await self._platform.assign_task(task.id, user_id)
        except Exception as exc:
            logger.warning(
                "dispatch.reassign_failed", task_id=task.id, user_id=user_id, error=str(exc)
            )
