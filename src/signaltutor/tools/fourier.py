from __future__ import annotations

import sympy as sp

from signaltutor.schemas.tools import ToolResult
from signaltutor.tools.common import failure_result, success_result


def fourier_transform(expression: sp.Expr, t: sp.Symbol, omega: sp.Symbol) -> ToolResult:
    try:
        result = sp.integrate(expression * sp.exp(-sp.I * omega * t), (t, -sp.oo, sp.oo))
        return success_result("fourier_transform", result, convention="angular_frequency")
    except Exception as exc:
        return failure_result("fourier_transform", "fourier_failed", exc)


def inverse_fourier_transform(expression: sp.Expr, omega: sp.Symbol, t: sp.Symbol) -> ToolResult:
    try:
        result = sp.integrate(expression * sp.exp(sp.I * omega * t), (omega, -sp.oo, sp.oo)) / (
            2 * sp.pi
        )
        return success_result("inverse_fourier_transform", result, convention="angular_frequency")
    except Exception as exc:
        return failure_result("inverse_fourier_transform", "inverse_fourier_failed", exc)
