from __future__ import annotations

import re

import sympy as sp

from signaltutor.schemas.tools import ToolResult
from signaltutor.tools.common import failure_result, success_result


def analyze_rational_z(expression: sp.Expr, z: sp.Symbol) -> ToolResult:
    try:
        numerator, denominator = sp.fraction(sp.cancel(expression))
        poles = sp.solve(denominator, z)
        zeros = sp.solve(numerator, z)
        return success_result(
            "analyze_rational_z",
            sp.cancel(expression),
            rational=bool(expression.is_rational_function(z)),
            poles=[str(pole) for pole in poles],
            zeros=[str(zero) for zero in zeros],
        )
    except Exception as exc:
        return failure_result("analyze_rational_z", "z_analysis_failed", exc)


def partial_fraction_in_z(expression: sp.Expr, z: sp.Symbol) -> ToolResult:
    try:
        result = sp.apart(expression, z)
        return success_result("partial_fraction_in_z", result)
    except Exception as exc:
        return failure_result("partial_fraction_in_z", "z_partial_fraction_failed", exc)


def check_roc_constraints(roc: str | None, poles: list[float]) -> ToolResult:
    if not roc:
        return ToolResult(
            success=False,
            tool_name="check_roc_constraints",
            evidence_id="check_roc_constraints:missing",
            error_code="missing_roc",
            error_message="仅有有理 X(z) 不能唯一确定时域序列，需要 ROC 或因果性等约束。",
        )
    normalized = re.sub(r"\s+", "", roc.lower()).replace("｜", "|")
    contains_unit_circle: bool | None = None
    outer_match = re.search(r"\|?z\|?>([0-9.]+)", normalized)
    inner_match = re.search(r"\|?z\|?<([0-9.]+)", normalized)
    if outer_match:
        contains_unit_circle = 1 > float(outer_match.group(1))
    elif inner_match:
        contains_unit_circle = 1 < float(inner_match.group(1))
    causal = bool(
        outer_match and poles and float(outer_match.group(1)) >= max(abs(p) for p in poles)
    )
    return success_result(
        "check_roc_constraints",
        roc,
        contains_unit_circle=contains_unit_circle,
        causal=causal,
    )
