from __future__ import annotations

import re

from signaltutor.agents.model_adapter import StructuredModel
from signaltutor.config.settings import Settings
from signaltutor.prompts import load_prompt
from signaltutor.schemas.classification import ProblemClassification
from signaltutor.schemas.problem import ProblemParse


def classify_deterministically(problem: ProblemParse) -> ProblemClassification:
    text = (problem.question_text + " " + " ".join(problem.known_conditions)).lower()
    contains_work = problem.contains_student_work
    if "z(" in text or "z)" in text or "z 变换" in text or "z变换" in text or "x(z)" in text:
        chapter, topics = "z_transform", ["inverse_transform", "roc"]
        tools, checks, errors = ["analyze_rational_z"], ["must_discuss_roc"], ["missing_roc"]
    elif "终值" in text or "初值" in text:
        topic = "final_value" if "终值" in text else "initial_value"
        chapter, topics = "laplace", [topic]
        tools = ["find_laplace_poles"]
        checks = ["check_fvt_poles" if topic == "final_value" else "check_ivt_conditions"]
        errors = ["final_value_without_pole_check"]
    elif "ctft" in text or "dtft" in text:
        chapter, topics = "fourier_transform", ["ctft" if "ctft" in text else "dtft"]
        tools, checks, errors = (
            ["fourier_transform"],
            ["check_2pi_convention"],
            ["fourier_2pi_error"],
        )
    elif "微分方程" in text and "系统函数" in text:
        chapter, topics = "lti", ["differential_equation"]
        tools, checks, errors = (
            ["solve_differential_equation"],
            ["zero_initial_conditions"],
            [],
        )
    elif (
        "卷积" in text
        or ("lti" in text and ("零状态" in text or "响应" in text))
        or all(token in text for token in ("x(t)", "h(t)", "y(t)"))
    ):
        chapter, topics = "lti", ["convolution"]
        tools = [
            "continuous_convolution"
            if problem.signal_domain != "discrete_time"
            else "discrete_convolution"
        ]
        checks, errors = (
            ["check_convolution_support"],
            ["wrong_convolution_bounds", "missing_step_function_support"],
        )
    elif "laplace" in text or "拉普拉斯" in text or re.search(r"[fxyh]\(s\)", text):
        chapter, topics = "laplace", ["transform", "system_function"]
        tools, checks, errors = ["laplace_transform"], ["check_roc"], ["transform_pair_error"]
    elif "fourier" in text or "傅里叶" in text or "频谱" in text:
        chapter, topics = "fourier_transform", ["ctft", "properties"]
        tools, checks, errors = (
            ["fourier_transform"],
            ["check_2pi_convention"],
            ["fourier_2pi_error"],
        )
    elif "采样" in text or "奈奎斯特" in text:
        chapter, topics = "sampling", ["nyquist", "aliasing"]
        tools, checks, errors = [], ["check_sampling_rate"], ["aliasing"]
    elif any(token in text for token in ("线性", "时不变", "因果", "稳定")):
        chapter, topics = (
            "system_properties",
            ["linearity", "time_invariance", "causality", "stability"],
        )
        tools, checks, errors = [], ["check_property_definitions"], ["unsupported_assumption"]
    else:
        chapter, topics = "signals", ["basic_operations"]
        tools, checks, errors = ["simplify_expression"], [], ["sign_error"]
    if contains_work:
        errors.append("wrong_frequency_domain_operation")
    return ProblemClassification(
        chapter=chapter,
        topics=topics,
        question_type="student_work_review" if contains_work else "calculation",
        difficulty=2,
        required_tools=tools,
        required_checks=checks,
        likely_error_patterns=errors,
    )


class ProblemClassifier:
    def __init__(self, model: StructuredModel | None, settings: Settings) -> None:
        self.model = model
        self.settings = settings

    async def classify(self, problem: ProblemParse) -> ProblemClassification:
        if not self.model or not self.settings.model_enabled:
            return classify_deterministically(problem)
        return await self.model.generate(
            name="SignalTutor Classifier",
            model=self.settings.models.classifier_model,
            instructions=load_prompt("classifier"),
            payload={"problem": problem.model_dump(), "taxonomy_rule": "use supplied taxonomy"},
            output_type=ProblemClassification,
        )
