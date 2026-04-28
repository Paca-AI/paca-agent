"""Application bootstrap — wires all components together and starts listening."""

from __future__ import annotations

from paca_agent.agent.dispatcher import TaskDispatcher
from paca_agent.config import ListenMode, Settings
from paca_agent.listeners.pull import PullListener
from paca_agent.listeners.push import PushListener
from paca_agent.platforms import build_platform
from paca_agent.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)


async def run() -> None:
    """Load configuration, wire components, and start the listener."""
    configure_logging()

    settings = Settings.load()
    logger.info(
        "paca_agent.start",
        platform=settings.platform.type,
        listen_mode=settings.listener.listen_mode,
        ai_account_id=settings.ai_account_id,
    )

    platform = build_platform(settings.platform)

    async with platform:
        dispatcher = TaskDispatcher(settings=settings, platform=platform)

        match settings.listener.listen_mode:
            case ListenMode.PULL:
                listener = PullListener(settings, platform, dispatcher)
            case ListenMode.PUSH:
                listener = PushListener(settings, platform, dispatcher)
            case _:
                raise ValueError(f"Unknown listen mode: {settings.listener.listen_mode!r}")

        await listener.start()
