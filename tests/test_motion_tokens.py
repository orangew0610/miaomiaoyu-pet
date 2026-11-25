from types import SimpleNamespace

from debug_pet_pyqt import PET_STATE_HAPPY, PET_STATE_WALKING_RIGHT, PetWindow


class FakeTimer:
    def __init__(self) -> None:
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


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
