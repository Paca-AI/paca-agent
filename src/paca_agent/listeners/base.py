"""Abstract base listener."""

from __future__ import annotations

from abc import ABC, abstractmethod

from paca_agent.agent.dispatcher import TaskDispatcher
from paca_agent.config import Settings
from paca_agent.platforms.base import BasePlatform


class BaseListener(ABC):
    """Contract for task listeners."""

    def __init__(
        self,
        settings: Settings,
        platform: BasePlatform,
        dispatcher: TaskDispatcher,
    ) -> None:
        self._settings = settings
        self._platform = platform
        self._dispatcher = dispatcher

    @abstractmethod
    async def start(self) -> None:
        """Start listening for new task assignments.  Should run until cancelled."""
