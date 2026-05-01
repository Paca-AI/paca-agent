"""Agent mode loader.

Loads agent mode definitions from Markdown files with YAML-style frontmatter.

Resolution order for ``<name>.md``:
1. ``agents/<name>.md`` relative to the current working directory (user-defined).
2. Built-in agents shipped with the package (``paca_agent/agents/<name>.md``).

Markdown file format::

    ---
    name: developer
    description: Expert software developer that implements features and fixes bugs.
    workflow: code
    ---

    You are an expert software developer AI agent. <rest of system prompt>

Supported ``workflow`` values
------------------------------
``code``
    The agent clones the repository, implements changes, commits, pushes, and
    opens a pull request.  This is the default when the field is absent.

``platform``
    The agent analyses the task and uses the project-management platform's MCP
    tools to create or update tasks, bugs, or comments.  No git operations or
    pull requests are performed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# Matches the YAML-style frontmatter block between the two ``---`` fences.
_FRONTMATTER_RE = re.compile(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n", re.DOTALL)
# Matches a single ``key: value`` pair inside the frontmatter.
_KV_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", re.MULTILINE)

# Directory that ships with the package containing the built-in agent files.
_BUILTIN_AGENTS_DIR = Path(__file__).parent.parent / "agents"

# Directory resolved at import time so tests can monkey-patch Path.cwd() cleanly.
_USER_AGENTS_DIR_NAME = "agents"

WorkflowType = Literal["code", "platform"]
_VALID_WORKFLOWS: frozenset[str] = frozenset({"code", "platform"})


@dataclass
class AgentMode:
    """Parsed agent mode definition."""

    name: str
    description: str
    system_prompt: str
    workflow: WorkflowType = field(default="code")


def _parse(text: str) -> AgentMode:
    """Parse a frontmatter + body markdown string into an :class:`AgentMode`."""
    m = _FRONTMATTER_RE.match(text)
    if m:
        frontmatter = m.group(1)
        body = text[m.end() :]
    else:
        frontmatter = ""
        body = text

    meta: dict[str, str] = {}
    for key, value in _KV_RE.findall(frontmatter):
        meta[key.lower()] = value.strip()

    name = meta.get("name", "custom")
    description = meta.get("description", "")
    system_prompt = body.strip()

    raw_workflow = meta.get("workflow", "code").lower()
    workflow: WorkflowType = raw_workflow if raw_workflow in _VALID_WORKFLOWS else "code"  # type: ignore[assignment]

    return AgentMode(
        name=name, description=description, system_prompt=system_prompt, workflow=workflow
    )


def load(agent_mode: str) -> AgentMode:
    """Load the agent mode definition for *agent_mode*.

    Searches the user ``agents/`` folder first, then the built-in agents.
    Raises :class:`FileNotFoundError` if the mode cannot be found.
    """
    filename = f"{agent_mode}.md"

    # 1. User-defined agents take precedence.
    user_path = Path.cwd() / _USER_AGENTS_DIR_NAME / filename
    if user_path.is_file():
        return _parse(user_path.read_text(encoding="utf-8"))

    # 2. Fall back to built-in agents.
    builtin_path = _BUILTIN_AGENTS_DIR / filename
    if builtin_path.is_file():
        return _parse(builtin_path.read_text(encoding="utf-8"))

    available = _list_available()
    raise FileNotFoundError(
        f"Agent mode '{agent_mode}' not found. "
        f"Available built-in modes: {available}. "
        f"You can also create 'agents/{filename}' in your project directory."
    )


def _list_available() -> list[str]:
    """Return names of all discoverable agent modes (built-in + user)."""
    names: set[str] = set()
    for path in _BUILTIN_AGENTS_DIR.glob("*.md"):
        names.add(path.stem)
    user_dir = Path.cwd() / _USER_AGENTS_DIR_NAME
    if user_dir.is_dir():
        for path in user_dir.glob("*.md"):
            names.add(path.stem)
    return sorted(names)
