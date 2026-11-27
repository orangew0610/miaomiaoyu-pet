from types import SimpleNamespace

from debug_pet_pyqt import (
    QApplication,
    PET_STATE_HAPPY,
    PET_STATE_IDLE,
    PET_STATE_JUMPING_RIGHT,
    PET_STATE_WALKING_RIGHT,
    PetWindow,
)


class FakeTimer:
    def __init__(self) -> None:
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True

    def start(self, interval=None) -> None:
        self.interval = interval


def motion_subject():
    return SimpleNamespace(
        _motion_token=0,
        _motion_mode=None,
        is_moving=False,
        parabola_timer=FakeTimer(),
    )


def test_replaced_motion_token_cannot_finish_new_motion() -> None:
    subject = motion_subject()
    old_token = PetWindow._begin_motion(subject, "walk")
    new_token = PetWindow._begin_motion(subject, "parabola")

    assert not PetWindow._finish_motion(subject, old_token)
    assert subject.is_moving
    assert subject._motion_mode == "parabola"
    assert PetWindow._finish_motion(subject, new_token)
    assert not subject.is_moving


def test_cancel_motion_invalidates_callbacks_and_stops_inertia_timer() -> None:
    subject = motion_subject()
    token = PetWindow._begin_motion(subject, "walk")

    PetWindow._cancel_motion(subject)

    assert subject._motion_token != token
    assert subject._motion_mode is None
    assert not subject.is_moving
    assert subject.parabola_timer.stopped


def test_parabola_landing_finishes_motion_before_switching_to_idle() -> None:
    switched = []
    subject = SimpleNamespace(
        parabola_data={
            "motion_token": 4,
            "current_step": 29,
            "steps": 30,
            "end_x": 120,
            "end_y": 500,
        },
        parabola_timer=FakeTimer(),
        _motion_token=4,
        _motion_mode="parabola",
        is_moving=True,
        current_state=PET_STATE_JUMPING_RIGHT,
        _place_pet_window=lambda _x, _y: None,
        _switch_animation=switched.append,
    )
    subject._finish_motion = lambda token: PetWindow._finish_motion(subject, token)
    subject._set_state = lambda state: PetWindow._set_state(subject, state)

    PetWindow._animate_parabola(subject)

    assert subject.parabola_timer.stopped
    assert subject._motion_mode is None
    assert not subject.is_moving
    assert subject.current_state == PET_STATE_IDLE
    assert switched == [PET_STATE_IDLE]


def test_non_motion_emotion_cannot_replace_active_walk_animation() -> None:
    switched = []
    subject = SimpleNamespace(
        _motion_mode="walk",
        current_state=PET_STATE_WALKING_RIGHT,
        _switch_animation=switched.append,
    )

    PetWindow._set_state(subject, PET_STATE_HAPPY)

    assert subject.current_state == PET_STATE_WALKING_RIGHT
    assert switched == []


def test_cursor_action_never_preempts_diagnostic_or_drag(monkeypatch) -> None:
    monkeypatch.setattr(QApplication, "activeModalWidget", lambda: None)
    subject = SimpleNamespace(
        is_dragging=False,
        _motion_mode=None,
        _diagnostic_busy=lambda: True,
    )
    assert not PetWindow._cursor_action_available(subject)

    subject._diagnostic_busy = lambda: False
    subject.is_dragging = True
    assert not PetWindow._cursor_action_available(subject)


def test_explicit_cursor_target_can_replace_walk_but_idle_attraction_cannot(
    monkeypatch,
) -> None:
    monkeypatch.setattr(QApplication, "activeModalWidget", lambda: None)
    subject = SimpleNamespace(
        is_dragging=False,
        _motion_mode="walk",
        _diagnostic_busy=lambda: False,
    )

    assert not PetWindow._cursor_action_available(subject)
    assert PetWindow._cursor_action_available(subject, allow_random_walk=True)


def test_only_matching_cursor_motion_starts_linger_timer() -> None:
    timer = FakeTimer()
    subject = SimpleNamespace(
        _cursor_motion_token=8,
        cursor_linger_timer=timer,
    )

    PetWindow._on_cursor_arrived(subject, 7)
    assert not hasattr(timer, "interval")

    PetWindow._on_cursor_arrived(subject, 8)
    assert subject._cursor_motion_token is None
    assert 6000 <= timer.interval <= 11000
