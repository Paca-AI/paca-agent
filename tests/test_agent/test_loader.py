"""Tests for the agent mode loader."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from paca_agent.agent.loader import AgentMode, _parse, load

# ---------------------------------------------------------------------------
# Unit tests for the internal parser
# ---------------------------------------------------------------------------


def test_parse_with_frontmatter() -> None:
    raw = textwrap.dedent("""\
        ---
        name: tester
        description: QA engineer that writes tests.
        workflow: platform
        ---

        You are a QA engineer.
    """)
    mode = _parse(raw)
    assert mode.name == "tester"
    assert mode.description == "QA engineer that writes tests."
    assert mode.system_prompt == "You are a QA engineer."
    assert mode.workflow == "platform"


def test_parse_without_frontmatter() -> None:
    raw = "You are an AI agent with no frontmatter."
    mode = _parse(raw)
    assert mode.name == "custom"
    assert mode.description == ""
    assert mode.system_prompt == "You are an AI agent with no frontmatter."
    assert mode.workflow == "code"  # default


def test_parse_missing_workflow_defaults_to_code() -> None:
    raw = textwrap.dedent("""\
        ---
        name: custom-agent
        description: A custom agent.
        ---

        You are a custom agent.
    """)
    mode = _parse(raw)
    assert mode.workflow == "code"


def test_parse_invalid_workflow_defaults_to_code() -> None:
    raw = textwrap.dedent("""\
        ---
        name: bad
        workflow: unknown-workflow-type
        ---

        You are an agent.
    """)
    mode = _parse(raw)
    assert mode.workflow == "code"


def test_parse_empty_body() -> None:
    raw = textwrap.dedent("""\
        ---
        name: planner
        description: Plans tasks.
        ---
    """)
    mode = _parse(raw)
    assert mode.name == "planner"
    assert mode.system_prompt == ""


# ---------------------------------------------------------------------------
# Integration tests: load() resolves built-in agents
# ---------------------------------------------------------------------------


def test_load_builtin_developer() -> None:
    mode = load("developer")
    assert isinstance(mode, AgentMode)
    assert mode.name == "developer"
    assert mode.system_prompt  # non-empty
    assert mode.workflow == "code"


def test_load_builtin_tester() -> None:
    mode = load("tester")
    assert mode.name == "tester"
    assert mode.system_prompt
    assert mode.workflow == "platform"


def test_load_builtin_planner() -> None:
    mode = load("planner")
    assert mode.name == "planner"
    assert mode.system_prompt
    assert mode.workflow == "platform"


def test_load_builtin_business_analyst() -> None:
    mode = load("business-analyst")
    assert mode.name == "business-analyst"
    assert mode.system_prompt
    assert mode.workflow == "platform"


def test_load_unknown_raises() -> None:
    with pytest.raises(FileNotFoundError, match="not found"):
        load("nonexistent-agent-xyz")


# ---------------------------------------------------------------------------
# User-defined agents in the local agents/ directory take priority
# ---------------------------------------------------------------------------


def test_user_agent_takes_priority_over_builtin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A user-defined agent with the same name as a built-in should win."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "developer.md").write_text(
        textwrap.dedent("""\
            ---
            name: developer
            description: Custom developer override.
            ---

            You are a custom developer agent.
        """),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    mode = load("developer")
    assert mode.system_prompt == "You are a custom developer agent."
    assert mode.description == "Custom developer override."


def test_user_agent_custom_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A user-defined agent with a name that has no built-in equivalent is loaded correctly."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "devops.md").write_text(
        textwrap.dedent("""\
            ---
            name: devops
            description: Infrastructure and DevOps specialist.
            workflow: code
            ---

            You are a DevOps engineer.
        """),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    mode = load("devops")
    assert mode.name == "devops"
    assert mode.system_prompt == "You are a DevOps engineer."
    assert mode.workflow == "code"


def test_user_agent_platform_workflow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A user-defined platform-workflow agent has workflow=='platform'."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "scrum-master.md").write_text(
        textwrap.dedent("""\
            ---
            name: scrum-master
            description: Scrum master agent.
            workflow: platform
            ---

            You are a scrum master.
        """),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    mode = load("scrum-master")
    assert mode.workflow == "platform"
