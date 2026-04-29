"""OpenHands SDK agent runner.

Responsible for:
- Spinning up an OpenHands Conversation inside a Docker sandbox
- Injecting the correct MCP tool servers (GitHub + optional platform)
- Running the agent to completion
- Extracting the PR URL (if any) from the agent's output
"""

from __future__ import annotations

import os
import re
import stat
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

from openhands.sdk import LLM, Agent, LocalConversation, Tool
from openhands.sdk.tool import register_tool
from openhands.sdk.workspace import LocalWorkspace
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool

from paca_agent.agent.prompts import build_task_prompt
from paca_agent.agent.tools import PRURLCapture, ReportPRTool, SetStatusTool, StatusCapture
from paca_agent.config import DockerSettings, GitHubSettings, LLMSettings
from paca_agent.models import Task
from paca_agent.platforms.base import BasePlatform
from paca_agent.utils.logging import get_logger

logger = get_logger(__name__)

_PR_URL_RE = re.compile(r"PR_CREATED:\s*(https://github\.com/\S+)", re.IGNORECASE)

# Name of the environment variable used to pass the GitHub token to the
# credential helper without embedding it in the script file.
_CREDENTIAL_TOKEN_ENV = "GIT_CREDENTIAL_TOKEN"


@contextmanager
def _inject_env(extras: dict[str, str]) -> Generator[None, None, None]:
    """Temporarily add *extras* to ``os.environ`` and restore on exit."""
    old: dict[str, str | None] = {k: os.environ.get(k) for k in extras}
    os.environ.update(extras)
    try:
        yield
    finally:
        for key, old_value in old.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


@dataclass
class RunResult:
    success: bool
    pr_url: str | None = None
    status: str | None = None
    summary: str | None = None
    error: str | None = None


class AgentRunner:
    """Runs an OpenHands agent inside a Docker sandbox for a single task."""

    def __init__(
        self,
        llm_settings: LLMSettings,
        github_settings: GitHubSettings,
        docker_settings: DockerSettings,
    ) -> None:
        self._llm_settings = llm_settings
        self._github_settings = github_settings
        self._docker_settings = docker_settings

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self, task: Task, platform: BasePlatform) -> RunResult:
        """Execute the agent for *task* and return a :class:`RunResult`."""
        logger.info("agent.run.start", task_id=task.id, task_type=task.task_type)

        # Fetch available statuses so the agent can pick the right one.
        # Failures are non-fatal — the dispatcher falls back to platform properties.
        available_statuses: list[str] = []
        try:
            available_statuses = await platform.get_available_statuses(task.id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("agent.run.statuses_fetch_failed", task_id=task.id, error=str(exc))

        mcp_config = self._build_mcp_config(task, platform)

        # Create per-run capture objects and register tools as fixed instances.
        # _resolver_from_instance is used, which returns the fixed instance without
        # any kwargs — avoiding the conv_state= mismatch in _resolver_from_callable.
        # Tasks run sequentially so re-registering is safe.
        pr_capture = PRURLCapture()
        register_tool("report_pr", ReportPRTool.create(pr_capture))

        status_capture = StatusCapture()
        register_tool("set_status", SetStatusTool.create(status_capture))

        llm = LLM(
            model=self._llm_settings.model,
            api_key=self._llm_settings.api_key.get_secret_value(),
            base_url=self._llm_settings.base_url,
        )

        tools = [
            Tool(name=TerminalTool.name),
            Tool(name=FileEditorTool.name),
            Tool(name="report_pr"),
            Tool(name="set_status"),
        ]

        agent = Agent(
            llm=llm,
            tools=tools,
            mcp_config=mcp_config,
        )

        try:
            with tempfile.TemporaryDirectory() as workdir:
                # Write a git credential helper that reads the token from an
                # environment variable so the token is never stored in the
                # script file itself.
                credential_helper_path = self._write_git_credential_helper(workdir)

                prompt = build_task_prompt(
                    task,
                    github_repo=self._github_settings.repo,
                    default_branch=self._github_settings.default_branch,
                    credential_helper_path=credential_helper_path,
                    committer_name=self._github_settings.committer_name,
                    committer_email=self._github_settings.committer_email,
                    available_statuses=available_statuses,
                )

                workspace = LocalWorkspace(working_dir=workdir)
                conversation = LocalConversation(
                    agent=agent,
                    workspace=workspace,
                )

                # Inject the token into the process environment only for the
                # duration of the conversation so the credential helper can
                # read it without the token ever appearing in a readable file.
                token = self._github_settings.token.get_secret_value()
                env_extras = {_CREDENTIAL_TOKEN_ENV: token} if token else {}
                with _inject_env(env_extras):
                    conversation.send_message(prompt)
                    result_events = conversation.run()

            last_message = self._extract_last_message(result_events)
            # Prefer the URL captured via the report_pr tool; fall back to regex on the final message.
            pr_url = pr_capture.pr_url or self._extract_pr_url(last_message)
            chosen_status = status_capture.status

            logger.info("agent.run.complete", task_id=task.id, pr_url=pr_url, status=chosen_status)
            return RunResult(
                success=True, pr_url=pr_url, status=chosen_status, summary=last_message
            )

        except Exception as exc:
            logger.exception("agent.run.failed", task_id=task.id, error=str(exc))
            return RunResult(success=False, error=str(exc))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_mcp_config(self, task: Task, platform: BasePlatform) -> dict | None:
        config: dict = {
            "mcpServers": {
                "github": {
                    "command": "docker",
                    "args": [
                        "run",
                        "-i",
                        "--rm",
                        "-e",
                        "GITHUB_PERSONAL_ACCESS_TOKEN",
                        "ghcr.io/github/github-mcp-server",
                    ],
                    "env": {
                        "GITHUB_PERSONAL_ACCESS_TOKEN": self._github_settings.token.get_secret_value(),
                    },
                },
            }
        }

        # Merge optional platform-specific MCP config
        platform_mcp = platform.mcp_config()
        if platform_mcp and "mcpServers" in platform_mcp:
            config["mcpServers"].update(platform_mcp["mcpServers"])

        return config

    def _write_git_credential_helper(self, workdir: str) -> str:
        """Write a git credential helper script that reads the token from the
        ``GIT_CREDENTIAL_TOKEN`` environment variable.

        The GitHub token is *never* written to disk — it is only referenced by
        name in the script so that even if the agent reads the file it cannot
        recover the credential.  The caller must inject the token into the
        process environment via :func:`_inject_env` before running the
        conversation.

        Returns the absolute path to the helper script, or an empty string when
        no token is configured (public repos).
        """
        token = self._github_settings.token.get_secret_value()
        if not token:
            return ""
        helper = Path(workdir) / ".git-credential-helper"
        helper.write_text(
            "#!/bin/sh\n"
            f"# Reads the GitHub token from the ${_CREDENTIAL_TOKEN_ENV} environment variable.\n"
            'echo "username=x-access-token"\n'
            f'echo "password=${{{_CREDENTIAL_TOKEN_ENV}}}"\n'
        )
        # Owner read+execute only — no write, no group/other access.
        # The file content is not sensitive (token comes from env), but we
        # still restrict access to avoid unnecessary exposure.
        helper.chmod(stat.S_IRUSR | stat.S_IXUSR)  # 0o500
        return str(helper)

    @staticmethod
    def _extract_last_message(events: object) -> str:
        if events is None:
            return ""
        # The SDK may return an iterable of events or a string
        if isinstance(events, str):
            return events
        try:
            all_events = list(events)  # type: ignore[arg-type]
            for event in reversed(all_events):
                if hasattr(event, "message"):
                    return str(event.message)
                if hasattr(event, "content"):
                    return str(event.content)
        except TypeError:
            pass
        return str(events)

    @staticmethod
    def _extract_pr_url(text: str) -> str | None:
        match = _PR_URL_RE.search(text)
        return match.group(1) if match else None
