from __future__ import annotations

import sympy as sp

from signaltutor.schemas.tools import ToolResult
from signaltutor.tools.common import failure_result, success_result


def simplify_expression(expression: sp.Expr) -> ToolResult:
    try:
        return success_result("simplify_expression", sp.simplify(expression))
    except Exception as exc:
        return failure_result("simplify_expression", "simplify_failed", exc)


def symbolic_integral(
    expression: sp.Expr, variable: sp.Symbol, lower: sp.Expr, upper: sp.Expr
) -> ToolResult:
    try:
        result = sp.integrate(expression, (variable, lower, upper))
        return success_result(
            "symbolic_integral", result, variable=str(variable), lower=str(lower), upper=str(upper)
        )
    except Exception as exc:
        return failure_result("symbolic_integral", "integral_failed", exc)


def solve_equation(equation: sp.Expr, variable: sp.Symbol) -> ToolResult:
    try:
        result = sp.solve(equation, variable)
        return success_result(
            "solve_equation", str(result), solutions=[str(item) for item in result]
        )
    except Exception as exc:
        return failure_result("solve_equation", "solve_failed", exc)


def solve_differential_equation(equation: sp.Eq, function: sp.Function) -> ToolResult:
    try:
        result = sp.dsolve(equation, function)
        return success_result("solve_differential_equation", str(result))
    except Exception as exc:
        return failure_result("solve_differential_equation", "differential_solve_failed", exc)


def partial_fraction(expression: sp.Expr, variable: sp.Symbol) -> ToolResult:
    try:
        return success_result("partial_fraction", sp.apart(expression, variable))
    except Exception as exc:
        return failure_result("partial_fraction", "partial_fraction_failed", exc)


def numeric_compare(
    left: sp.Expr, right: sp.Expr, variable: sp.Symbol, samples: list[float] | None = None
) -> ToolResult:
    values = samples or [0.17, 0.61, 1.19, 2.03]
    try:
        delta = sp.lambdify(variable, left - right, "numpy")
        errors = [abs(complex(delta(value))) for value in values]
        equivalent = max(errors, default=0.0) < 1e-8
        return ToolResult(
            success=True,
            tool_name="numeric_compare",
            evidence_id=f"numeric_compare:{abs(hash(tuple(values))):x}",
            result_text=str(equivalent),
            metadata={"equivalent": equivalent, "max_error": max(errors, default=0.0)},
        )
    except Exception as exc:
        return failure_result("numeric_compare", "numeric_compare_failed", exc)
