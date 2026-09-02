from __future__ import annotations

import sympy as sp

from signaltutor.schemas.tools import ToolResult
from signaltutor.tools.common import failure_result, success_result


def find_poles(expression: sp.Expr, variable: sp.Symbol) -> ToolResult:
    try:
        _, denominator = sp.fraction(sp.cancel(expression))
        poles = sp.solve(denominator, variable)
        return success_result("find_poles", str(poles), poles=[str(pole) for pole in poles])
    except Exception as exc:
        return failure_result("find_poles", "pole_search_failed", exc)


def find_zeros(expression: sp.Expr, variable: sp.Symbol) -> ToolResult:
    try:
        numerator, _ = sp.fraction(sp.cancel(expression))
        zeros = sp.solve(numerator, variable)
        return success_result("find_zeros", str(zeros), zeros=[str(zero) for zero in zeros])
    except Exception as exc:
        return failure_result("find_zeros", "zero_search_failed", exc)


def check_stability_from_roc(contains_unit_circle: bool | None) -> ToolResult:
    if contains_unit_circle is None:
        return ToolResult(
            success=False,
            tool_name="check_stability_from_roc",
            evidence_id="check_stability_from_roc:unknown",
            error_code="unknown_roc",
            error_message="无法判断 ROC 是否包含单位圆。",
        )
    return success_result(
        "check_stability_from_roc", str(contains_unit_circle), stable=contains_unit_circle
    )
