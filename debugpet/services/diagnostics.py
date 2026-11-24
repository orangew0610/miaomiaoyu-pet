from __future__ import annotations

import time
from dataclasses import dataclass
from enum import IntEnum


class Severity(IntEnum):
    ERROR = 1
    WARNING = 2
    INFORMATION = 3
    HINT = 4


@dataclass(frozen=True, slots=True)
class DiagnosticEvent:
    uri: str
    version: int
    severity: Severity
    message: str
    line: int
    character: int
    end_line: int
    end_character: int
    removed: bool = False

    @property
    def identity(self) -> tuple[object, ...]:
        return (
            self.uri,
            self.severity,
            self.message,
            self.line,
            self.character,
            self.end_line,
            self.end_character,
        )


class DiagnosticGate:
    """Validate versions, filter severities, deduplicate, and apply cooldowns."""

    def __init__(
        self,
        maximum_severity: Severity = Severity.WARNING,
        cooldown_seconds: float = 5.0,
        clock=time.monotonic,
    ) -> None:
        self.maximum_severity = maximum_severity
        self.cooldown_seconds = cooldown_seconds
        self._clock = clock
        self._versions: dict[str, int] = {}
        self._last_seen: dict[tuple[object, ...], float] = {}

    def accept(self, event: DiagnosticEvent) -> bool:
        current_version = self._versions.get(event.uri, -1)
        if event.version < current_version:
            return False
        self._versions[event.uri] = event.version

        if not event.removed and event.severity > self.maximum_severity:
            return False
        if event.removed:
            self._last_seen.pop(event.identity, None)
            return True

        now = self._clock()
        last_seen = self._last_seen.get(event.identity)
        if last_seen is not None and now - last_seen < self.cooldown_seconds:
            return False
        self._last_seen[event.identity] = now
        return True
