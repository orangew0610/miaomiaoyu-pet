from debugpet.services.diagnostics import DiagnosticEvent, DiagnosticGate, Severity


def event(**changes) -> DiagnosticEvent:
    values = {
        "uri": "file:///workspace/main.py",
        "version": 3,
        "severity": Severity.ERROR,
        "message": "undefined name",
        "line": 4,
        "character": 2,
        "end_line": 4,
        "end_character": 8,
    }
    values.update(changes)
    return DiagnosticEvent(**values)


def test_duplicate_is_suppressed_during_cooldown() -> None:
    now = [100.0]
    gate = DiagnosticGate(cooldown_seconds=5, clock=lambda: now[0])
    assert gate.accept(event())
    assert not gate.accept(event())
    now[0] += 5
    assert gate.accept(event())


def test_stale_file_version_is_rejected() -> None:
    gate = DiagnosticGate()
    assert gate.accept(event(version=5))
    assert not gate.accept(event(version=4, message="new diagnostic"))


def test_severity_filter_and_removed_event() -> None:
    gate = DiagnosticGate(maximum_severity=Severity.WARNING)
    assert not gate.accept(event(severity=Severity.INFORMATION))
    assert gate.accept(event(removed=True))
