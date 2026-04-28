"""Entry point for `python -m paca_agent` and the `paca-agent` CLI script."""

from __future__ import annotations

import sys

import anyio

from paca_agent.app import run


def main() -> None:
    """Start paca-agent."""
    try:
        anyio.run(run)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
