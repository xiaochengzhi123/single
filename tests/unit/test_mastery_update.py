import pytest

from signaltutor.students.mastery import update_mastery


def test_mastery_uses_ema_and_clamps() -> None:
    assert update_mastery(0.5, 1.0) == pytest.approx(0.6)
    assert update_mastery(1.0, 2.0) == 1.0
    assert update_mastery(0.0, -1.0) == 0.0
