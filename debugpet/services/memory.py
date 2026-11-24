from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MemoryService(ABC):
    """Stable boundary for future short- and long-term memory backends."""

    @abstractmethod
    def remember(self, namespace: str, item: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def recall(self, namespace: str, limit: int = 20) -> list[dict[str, Any]]:
        raise NotImplementedError


class NullMemoryService(MemoryService):
    def remember(self, namespace: str, item: dict[str, Any]) -> None:
        return None

    def recall(self, namespace: str, limit: int = 20) -> list[dict[str, Any]]:
        return []
