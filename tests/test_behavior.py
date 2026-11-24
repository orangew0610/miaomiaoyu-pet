import pytest

from debugpet.services.behavior import BehaviorState, DiagnosticBehavior


def test_complete_behavior_sequence() -> None:
    behavior = DiagnosticBehavior()
    behavior.detect("error-1")
    behavior.locating()
    behavior.navigate((500, 300), precise=True)
    behavior.arrived()
    behavior.report()
    behavior.wait()
    assert behavior.celebrate("error-1")
    assert behavior.history == [
        BehaviorState.DETECT, BehaviorState.LOCATE, BehaviorState.NAVIGATE,
        BehaviorState.ARRIVE, BehaviorState.REPORT, BehaviorState.WAIT,
        BehaviorState.CELEBRATE,
    ]


def test_wrong_error_cannot_trigger_celebration() -> None:
    behavior = DiagnosticBehavior()
    behavior.detect("error-1")
    behavior.locating()
    assert not behavior.celebrate("error-2")
    assert behavior.state == BehaviorState.LOCATE


def test_drag_or_window_switch_cancels_navigation() -> None:
    behavior = DiagnosticBehavior()
    behavior.detect("error-1")
    behavior.locating()
    behavior.navigate((1, 2), precise=True)
    assert behavior.cancel("pet-dragged")
    assert behavior.state == BehaviorState.CANCELLED
    assert behavior.task.cancellation_reason == "pet-dragged"


def test_report_before_arrival_is_rejected() -> None:
    behavior = DiagnosticBehavior()
    behavior.detect("error-1")
    with pytest.raises(RuntimeError):
        behavior.report()
