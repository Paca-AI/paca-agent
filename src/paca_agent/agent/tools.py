"""Custom OpenHands SDK tools for paca-agent."""

from __future__ import annotations

from collections.abc import Sequence

from openhands.sdk import Action, ImageContent, Observation, TextContent, ToolDefinition
from openhands.sdk.tool import ToolExecutor
from pydantic import Field

# ---------------------------------------------------------------------------
# SetStatusTool — lets the agent record the desired task status
# ---------------------------------------------------------------------------

_SET_STATUS_DESCRIPTION = """Record the task status to be set in the project management system.
Call this tool after completing all work (and after calling report_pr if a PR was created).
You MUST pass an exact status name from the available statuses list shown in your instructions.
The system will use this value to update the task — do NOT guess or invent a name."""


class SetStatusAction(Action):
    status: str = Field(
        description=(
            "The exact status name to set on the task. "
            "Must be one of the available statuses listed in your instructions."
        )
    )


class SetStatusObservation(Observation):
    recorded: bool = True

    @property
    def to_llm_content(self) -> Sequence[TextContent | ImageContent]:
        return [
            TextContent(text="Status recorded. The system will update the task status accordingly.")
        ]


class StatusCapture:
    """Mutable container written by the executor, read by the runner after the conversation ends."""

    def __init__(self) -> None:
        self.status: str | None = None


class _SetStatusExecutor(ToolExecutor[SetStatusAction, SetStatusObservation]):
    def __init__(self, capture: StatusCapture) -> None:
        self._capture = capture

    def __call__(
        self,
        action: SetStatusAction,
        conversation: object = None,  # noqa: ARG002
    ) -> SetStatusObservation:
        self._capture.status = action.status
        return SetStatusObservation()


class SetStatusTool(ToolDefinition[SetStatusAction, SetStatusObservation]):
    """Custom tool that lets the agent hand the chosen task status back to the runner."""

    @classmethod
    def create(cls, capture: StatusCapture) -> SetStatusTool:
        return cls(
            description=_SET_STATUS_DESCRIPTION,
            action_type=SetStatusAction,
            observation_type=SetStatusObservation,
            executor=_SetStatusExecutor(capture),
        )


# ---------------------------------------------------------------------------
# ReportPRTool — lets the agent hand the PR URL back to the runner
# ---------------------------------------------------------------------------

_REPORT_PR_DESCRIPTION = """Record the URL of a pull request that was just created.
Call this tool immediately after successfully creating a pull request.
Pass the full PR URL so the system can track it for follow-up actions such as
status updates and reviewer assignment."""


class ReportPRAction(Action):
    pr_url: str = Field(
        description="The full URL of the created pull request (e.g. https://github.com/owner/repo/pull/42)"
    )


class ReportPRObservation(Observation):
    recorded: bool = True

    @property
    def to_llm_content(self) -> Sequence[TextContent | ImageContent]:
        return [TextContent(text="PR URL recorded successfully. Task complete.")]


class PRURLCapture:
    """Mutable container written by the executor and read by the runner after the conversation ends."""

    def __init__(self) -> None:
        self.pr_url: str | None = None


class _ReportPRExecutor(ToolExecutor[ReportPRAction, ReportPRObservation]):
    def __init__(self, capture: PRURLCapture) -> None:
        self._capture = capture

    def __call__(
        self,
        action: ReportPRAction,
        conversation: object = None,  # noqa: ARG002
    ) -> ReportPRObservation:
        self._capture.pr_url = action.pr_url
        return ReportPRObservation()


class ReportPRTool(ToolDefinition[ReportPRAction, ReportPRObservation]):
    """Custom tool that lets the agent hand the PR URL back to the runner directly."""

    @classmethod
    def create(cls, capture: PRURLCapture) -> ReportPRTool:
        return cls(
            description=_REPORT_PR_DESCRIPTION,
            action_type=ReportPRAction,
            observation_type=ReportPRObservation,
            executor=_ReportPRExecutor(capture),
        )
