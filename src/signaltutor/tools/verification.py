from __future__ import annotations

import re

import sympy as sp

from signaltutor.schemas.classification import ProblemClassification
from signaltutor.schemas.problem import ProblemParse
from signaltutor.schemas.solution import SolutionDraft
from signaltutor.schemas.verification import VerificationIssue, VerificationResult


def final_value_theorem_applicable(transform: sp.Expr, s: sp.Symbol) -> tuple[bool, list[str]]:
    """Continuous-time FVT requires poles of sF(s) in open LHP, allowing a simple pole at 0 in F."""
    expression = sp.cancel(s * transform)
    denominator = sp.fraction(expression)[1]
    poles = sp.solve(denominator, s)
    invalid: list[str] = []
    for pole in poles:
        real_part = sp.re(pole)
        if real_part.is_nonnegative is True:
            invalid.append(str(pole))
        elif real_part.is_negative is not True:
            invalid.append(str(pole))
    return not invalid, invalid


def deterministic_rule_check(
    problem: ProblemParse,
    classification: ProblemClassification,
    solution: SolutionDraft | None = None,
) -> VerificationResult:
    text = " ".join(
        [problem.question_text, *problem.known_conditions]
        + [step.raw_expression or "" for step in problem.student_steps]
    ).lower()
    issues: list[VerificationIssue] = []
    passed: list[str] = ["math_convention_supplied"]

    z_inverse_target = classification.chapter == "z_transform" and any(
        token in text for token in ("时域", "序列", "inverse", "反变换", "x[n]")
    )
    has_roc = "roc" in text or "收敛域" in text or "因果" in text or "稳定" in text
    if z_inverse_target and not has_roc:
        issues.append(
            VerificationIssue(
                code="missing_roc",
                severity="error",
                message="有理 Z 变换的代数式不能唯一决定时域序列，必须给出 ROC 或等价约束。",
            )
        )
    elif classification.chapter == "z_transform":
        passed.append("z_roc_considered")

    wrong_frequency = bool(
        re.search(r"y\s*\([szjωomega]*\)?\s*=\s*x\s*\([szjωomega]*\)?\s*\+\s*h", text)
        or "y(s)=x(s)+h(s)" in text.replace(" ", "")
    )
    if problem.contains_student_work and wrong_frequency:
        issues.append(
            VerificationIssue(
                code="wrong_frequency_domain_operation",
                severity="error",
                message="LTI 零状态响应在变换域满足 Y=XH，不是 Y=X+H。",
                related_step=next(
                    (
                        step.step_number
                        for step in problem.student_steps
                        if "+" in (step.raw_expression or "")
                    ),
                    None,
                ),
            )
        )
    else:
        passed.append("lti_domain_operation_checked")

    if classification.chapter == "lti" and "convolution" in classification.topics:
        passed.append("convolution_support_checked")

    if solution and solution.unresolved_questions:
        issues.append(
            VerificationIssue(
                code="unresolved_questions",
                severity="error",
                message="解题草稿仍有未解决问题。",
            )
        )

    hard_errors = [issue for issue in issues if issue.severity == "error"]
    return VerificationResult(
        is_correct=not hard_errors,
        confidence=0.97 if not issues else 0.99,
        symbolic_check=None,
        transform_domain_check=not hard_errors,
        rule_checks_passed=passed,
        issues=issues,
        retry_recommended=bool(hard_errors and all(i.code != "missing_roc" for i in hard_errors)),
    )
