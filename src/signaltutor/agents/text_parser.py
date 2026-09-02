from __future__ import annotations

import re

from signaltutor.schemas.problem import FormulaItem, ProblemParse, StudentWorkStep


def parse_text_problem(content: str, student_work: str | None = None) -> ProblemParse:
    normalized = content.strip()
    lower = normalized.lower()
    formulas: list[FormulaItem] = []
    formula_pattern = re.compile(
        r"(?:[xXhHyY]\s*\([tzs]\)|[xXhHyY]\s*\[[nNkK]\])\s*=\s*[^，,。;；\n]+"
    )
    for match in formula_pattern.findall(normalized):
        formulas.append(FormulaItem(raw=match, latex=match, confidence=1.0))
    if "z" in lower and ("x(z)" in lower or "z 变换" in lower or "z变换" in lower):
        domain = "discrete_time"
    elif "[n]" in lower or "离散" in normalized:
        domain = "discrete_time"
    elif "(t)" in lower or "连续" in normalized:
        domain = "continuous_time"
    else:
        domain = "unknown"
    target_match = re.search(r"(?:求|判断|证明)([^。\n]+)", normalized)
    target = target_match.group(0) if target_match else "回答题目所问"
    conditions = [part.strip() for part in re.split(r"[，,；;\n]", normalized) if part.strip()]
    student_steps: list[StudentWorkStep] = []
    if student_work:
        for index, step in enumerate(filter(None, re.split(r"[\n；;]+", student_work)), start=1):
            student_steps.append(
                StudentWorkStep(
                    step_number=index, raw_expression=step.strip(), description=step.strip()
                )
            )
    return ProblemParse(
        input_type="text",
        question_text=normalized,
        known_conditions=conditions,
        target=target,
        formulas=formulas,
        figures=[],
        uncertain_elements=[],
        contains_student_work=bool(student_steps),
        student_steps=student_steps,
        signal_domain=domain,
        confidence=1.0,
    )
