from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Hashable


class BehaviorState(str, Enum):
    IDLE = "IDLE"
    DETECT = "DETECT"
    LOCATE = "LOCATE"
    NAVIGATE = "NAVIGATE"
    ARRIVE = "ARRIVE"
    REPORT = "REPORT"
    WAIT = "WAIT"
    CELEBRATE = "CELEBRATE"
    CANCELLED = "CANCELLED"


@dataclass(slots=True)
class NavigationTask:
    identity: Hashable
    state: BehaviorState = BehaviorState.DETECT
    precise: bool = False
    target: tuple[int, int] | None = None
    cancellation_reason: str | None = None


class DiagnosticBehavior:
    """Strict state transitions for one diagnostic navigation task."""

    def __init__(self) -> None:
        self.task: NavigationTask | None = None
        self.history: list[BehaviorState] = []

    @property
    def state(self) -> BehaviorState:
        return self.task.state if self.task else BehaviorState.IDLE

    def _transition(self, expected: set[BehaviorState], target: BehaviorState) -> None:
        if not self.task or self.task.state not in expected:
            raise RuntimeError(f"invalid behavior transition {self.state} -> {target}")
        self.task.state = target
        self.history.append(target)

    def detect(self, identity: Hashable) -> NavigationTask:
        if self.task and self.task.state not in {
            BehaviorState.WAIT, BehaviorState.CELEBRATE,
            BehaviorState.CANCELLED,
        }:
            self.cancel("superseded")
        self.task = NavigationTask(identity=identity)
        self.history.append(BehaviorState.DETECT)
        return self.task

    def locating(self) -> None:
        self._transition({BehaviorState.DETECT}, BehaviorState.LOCATE)

    def navigate(self, target: tuple[int, int], *, precise: bool) -> None:
        if not self.task:
            raise RuntimeError("no active task")
        self.task.target = target
        self.task.precise = precise
        self._transition({BehaviorState.LOCATE}, BehaviorState.NAVIGATE)

    def arrived(self) -> None:
        self._transition({BehaviorState.NAVIGATE}, BehaviorState.ARRIVE)

    def report(self) -> None:
        self._transition({BehaviorState.ARRIVE}, BehaviorState.REPORT)

    def wait(self) -> None:
        self._transition({BehaviorState.REPORT}, BehaviorState.WAIT)

    def celebrate(self, identity: Hashable) -> bool:
        if not self.task or self.task.identity != identity:
            return False
        self._transition(
            {
                BehaviorState.DETECT, BehaviorState.LOCATE, BehaviorState.NAVIGATE,
                BehaviorState.ARRIVE, BehaviorState.REPORT, BehaviorState.WAIT,
            },
            BehaviorState.CELEBRATE,
        )
        return True

    def cancel(self, reason: str) -> bool:
        if not self.task or self.task.state in {
            BehaviorState.CANCELLED, BehaviorState.CELEBRATE,
        }:
            return False
        self.task.cancellation_reason = reason
        self.task.state = BehaviorState.CANCELLED
        self.history.append(BehaviorState.CANCELLED)
        return True
