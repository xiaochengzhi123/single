from signaltutor.schemas.classification import ProblemClassification
from signaltutor.schemas.problem import FormulaItem, ProblemParse
from signaltutor.tools.verification import deterministic_rule_check


def test_inverse_z_without_roc_is_blocked() -> None:
    problem = ProblemParse(
        input_type="text",
        question_text="已知 X(z)=z/(z-a)，求时域序列 x[n]。",
        known_conditions=[],
        target="求 x[n]",
        formulas=[FormulaItem(raw="X(z)=z/(z-a)", latex=r"X(z)=\frac z{z-a}", confidence=1)],
        signal_domain="discrete_time",
        confidence=1,
    )
    classification = ProblemClassification(
        chapter="z_transform",
        topics=["inverse_transform", "roc"],
        question_type="calculation",
        difficulty=2,
        required_tools=["analyze_rational_z"],
        required_checks=["must_discuss_roc"],
        likely_error_patterns=["missing_roc"],
    )
    result = deterministic_rule_check(problem, classification)
    assert not result.is_correct
    assert result.issues[0].code == "missing_roc"
