from __future__ import annotations

import re

import sympy as sp


def normalized_problem_text(text: str) -> str:
    return re.sub(r"\s+", "", text).lower().replace("（", "(").replace("）", ")")


def safe_sympify(expression: str, symbols: dict[str, sp.Symbol] | None = None) -> sp.Expr:
    local_dict: dict[str, object] = {
        "exp": sp.exp,
        "sin": sp.sin,
        "cos": sp.cos,
        "Heaviside": sp.Heaviside,
        "DiracDelta": sp.DiracDelta,
        "I": sp.I,
        "pi": sp.pi,
    }
    local_dict.update(symbols or {})
    return sp.sympify(expression, locals=local_dict)
