from __future__ import annotations

import sympy as sp

from signaltutor.schemas.tools import ToolResult
from signaltutor.tools.common import failure_result, success_result


def laplace_transform(expression: sp.Expr, t: sp.Symbol, s: sp.Symbol) -> ToolResult:
    try:
        result, convergence, condition = sp.laplace_transform(expression, t, s)
        return success_result(
            "laplace_transform",
            result,
            convergence_plane=str(convergence),
            condition=str(condition),
        )
    except Exception as exc:
        return failure_result("laplace_transform", "laplace_failed", exc)


def inverse_laplace_transform(expression: sp.Expr, s: sp.Symbol, t: sp.Symbol) -> ToolResult:
    try:
        result = sp.inverse_laplace_transform(expression, s, t)
        return success_result("inverse_laplace_transform", result)
    except Exception as exc:
        return failure_result("inverse_laplace_transform", "inverse_laplace_failed", exc)


def find_laplace_poles(expression: sp.Expr, s: sp.Symbol) -> ToolResult:
    try:
        _, denominator = sp.fraction(sp.cancel(expression))
        poles = sp.solve(denominator, s)
        return success_result("find_laplace_poles", str(poles), poles=[str(pole) for pole in poles])
    except Exception as exc:
        return failure_result("find_laplace_poles", "pole_search_failed", exc)
