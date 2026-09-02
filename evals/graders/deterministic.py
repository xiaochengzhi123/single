from __future__ import annotations

import re
from dataclasses import dataclass

import sympy as sp


@dataclass(frozen=True)
class Grade:
    topic_recall: float
    required_checks_recall: float
    forbidden_error_count: int
    symbolic_equivalent: bool | None


def symbolic_equivalent(left: str, right: str, variable: str = "t") -> bool | None:
    try:
        symbol = sp.Symbol(variable, real=True)
        locals_map = {variable: symbol, "u": sp.Heaviside, "exp": sp.exp}
        return (
            sp.simplify(sp.sympify(left, locals=locals_map) - sp.sympify(right, locals=locals_map))
            == 0
        )
    except (sp.SympifyError, TypeError, ValueError):
        return None


def grade_text(answer: str, example: dict) -> Grade:
    normalized = re.sub(r"\s+", "", answer.lower())
    topics = example.get("required_topics", [])
    checks = example.get("required_checks", [])
    forbidden = example.get("forbidden_errors", [])
    topic_hits = sum(topic.lower() in normalized for topic in topics)
    check_hits = sum(check.lower() in normalized for check in checks)
    forbidden_hits = sum(code.lower() in normalized for code in forbidden)
    return Grade(
        topic_recall=topic_hits / len(topics) if topics else 1.0,
        required_checks_recall=check_hits / len(checks) if checks else 1.0,
        forbidden_error_count=forbidden_hits,
        symbolic_equivalent=None,
    )
