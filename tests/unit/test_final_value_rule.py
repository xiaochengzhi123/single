import sympy as sp

from signaltutor.tools.verification import final_value_theorem_applicable


def test_final_value_accepts_stable_case() -> None:
    s = sp.Symbol("s")
    ok, invalid = final_value_theorem_applicable(1 / (s * (s + 1)), s)
    assert ok
    assert invalid == []


def test_final_value_rejects_right_half_plane_pole() -> None:
    s = sp.Symbol("s")
    ok, invalid = final_value_theorem_applicable(1 / (s * (s - 1)), s)
    assert not ok
    assert "1" in invalid
