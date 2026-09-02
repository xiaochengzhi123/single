from __future__ import annotations

from collections.abc import Sequence

import sympy as sp

from signaltutor.schemas.tools import ToolResult
from signaltutor.tools.common import failure_result, success_result


def continuous_convolution(
    x_tau: sp.Expr,
    h_t_minus_tau: sp.Expr,
    tau: sp.Symbol,
    lower: sp.Expr,
    upper: sp.Expr,
    support_latex: str | None = None,
) -> ToolResult:
    """Integrate a continuous convolution after explicit support intersection."""
    try:
        result = sp.simplify(sp.integrate(x_tau * h_t_minus_tau, (tau, lower, upper)))
        return success_result(
            "continuous_convolution",
            result,
            lower=str(lower),
            upper=str(upper),
            support=support_latex,
        )
    except Exception as exc:
        return failure_result("continuous_convolution", "convolution_failed", exc)


def causal_exponential_convolution(
    input_decay: sp.Expr, impulse_decay: sp.Expr, t: sp.Symbol | None = None
) -> ToolResult:
    """Convolution of exp(-a t)u(t) and exp(-b t)u(t), retaining support."""
    time = t or sp.Symbol("t", real=True)
    tau = sp.Symbol("tau", real=True)
    try:
        integrand = sp.exp(-input_decay * tau) * sp.exp(-impulse_decay * (time - tau))
        core = sp.expand(sp.integrate(integrand, (tau, 0, time)))
        result = core * sp.Heaviside(time)
        output = success_result(
            "continuous_convolution",
            result,
            lower="0",
            upper=str(time),
            support=f"{time} >= 0",
            input_decay=str(input_decay),
            impulse_decay=str(impulse_decay),
        )
        output.result_latex = rf"\left({sp.latex(core)}\right)u\left({sp.latex(time)}\right)"
        return output
    except Exception as exc:
        return failure_result("continuous_convolution", "convolution_failed", exc)


def discrete_convolution(x: Sequence[sp.Expr], h: Sequence[sp.Expr]) -> ToolResult:
    try:
        output = [sp.Integer(0)] * (len(x) + len(h) - 1)
        for n, x_n in enumerate(x):
            for k, h_k in enumerate(h):
                output[n + k] += sp.sympify(x_n) * sp.sympify(h_k)
        simplified = [sp.simplify(item) for item in output]
        return success_result(
            "discrete_convolution", str(simplified), values=[str(item) for item in simplified]
        )
    except Exception as exc:
        return failure_result("discrete_convolution", "convolution_failed", exc)
