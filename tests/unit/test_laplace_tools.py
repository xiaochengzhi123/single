import sympy as sp

from signaltutor.tools.laplace import find_laplace_poles, laplace_transform


def test_laplace_of_causal_exponential() -> None:
    t, s = sp.symbols("t s", positive=True)
    result = laplace_transform(sp.exp(-2 * t), t, s)
    assert result.success
    assert sp.simplify(sp.sympify(result.result_text, locals={"s": s}) - 1 / (s + 2)) == 0


def test_find_poles() -> None:
    s = sp.Symbol("s")
    result = find_laplace_poles(1 / ((s + 1) * (s + 2)), s)
    assert result.success
    assert set(result.metadata["poles"]) == {"-1", "-2"}
