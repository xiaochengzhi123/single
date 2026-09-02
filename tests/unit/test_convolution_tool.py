import sympy as sp

from signaltutor.tools.convolution import causal_exponential_convolution, discrete_convolution


def test_causal_exponential_convolution() -> None:
    t = sp.Symbol("t", positive=True)
    result = causal_exponential_convolution(sp.Integer(2), sp.Integer(1), t)
    assert result.success
    actual = sp.sympify(result.result_text, locals={"t": t})
    expected = sp.exp(-t) - sp.exp(-2 * t)
    assert sp.simplify(actual - expected) == 0
    assert result.metadata["lower"] == "0"
    assert result.metadata["upper"] == "t"


def test_discrete_convolution() -> None:
    result = discrete_convolution([1, 2], [1, 1])
    assert result.success
    assert result.metadata["values"] == ["1", "3", "2"]
