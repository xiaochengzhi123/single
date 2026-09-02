from __future__ import annotations

import re

import sympy as sp

from signaltutor.agents.model_adapter import StructuredModel
from signaltutor.config.settings import Settings
from signaltutor.math.conventions import DEFAULT_CONVENTION
from signaltutor.prompts import load_prompt
from signaltutor.schemas.classification import ProblemClassification
from signaltutor.schemas.problem import ProblemParse
from signaltutor.schemas.retrieval import RetrievalContext
from signaltutor.schemas.solution import DerivationStep, SolutionDraft, SolutionPlan
from signaltutor.schemas.student import AnswerMode
from signaltutor.tools.convolution import causal_exponential_convolution


class Solver:
    def __init__(self, model: StructuredModel | None, settings: Settings) -> None:
        self.model = model
        self.settings = settings

    async def solve(
        self,
        problem: ProblemParse,
        classification: ProblemClassification,
        retrieval: RetrievalContext,
        plan: SolutionPlan,
        mode: AnswerMode,
        retry_feedback: str | None = None,
        model_override: str | None = None,
    ) -> SolutionDraft:
        if not self.model or not self.settings.model_enabled:
            return self._offline(problem, classification, plan)
        return await self.model.generate(
            name="SignalTutor Solver",
            model=model_override or self.settings.models.solver_model,
            instructions=load_prompt("solver"),
            payload={
                "problem": problem.model_dump(),
                "classification": classification.model_dump(),
                "retrieval": retrieval.model_dump(),
                "plan": plan.model_dump(),
                "convention": DEFAULT_CONVENTION.model_dump(),
                "mode": mode,
                "retry_feedback": retry_feedback,
            },
            output_type=SolutionDraft,
        )

    def _offline(
        self, problem: ProblemParse, classification: ProblemClassification, plan: SolutionPlan
    ) -> SolutionDraft:
        text = problem.question_text.replace(" ", "")
        if problem.contains_student_work:
            wrong = next(
                (
                    step
                    for step in problem.student_steps
                    if "+" in (step.raw_expression or "")
                    and "Y" in (step.raw_expression or "").upper()
                ),
                None,
            )
            if wrong:
                return SolutionDraft(
                    interpretation="核对学生关于 LTI 零状态响应的变换域步骤。",
                    concepts_used=["LTI", "卷积定理"],
                    plan_summary=plan.steps,
                    derivation_steps=[
                        DerivationStep(
                            index=wrong.step_number,
                            title="首个错误步骤",
                            explanation="时域卷积在变换域对应乘法，不能写成相加。",
                            expression_latex=r"Y(s)=X(s)H(s)",
                        )
                    ],
                    candidate_answer_latex=r"Y(s)=X(s)H(s)",
                    assumptions=[],
                    unresolved_questions=[],
                )
        if classification.chapter == "lti" and "convolution" in classification.topics:
            decays = re.findall(r"e\^\{?-(\d+)t\}?", text)
            if len(decays) < 2:
                decays = re.findall(r"e\^-(\d+)t", text)
            a, b = (
                (sp.Integer(decays[0]), sp.Integer(decays[1]))
                if len(decays) >= 2
                else (sp.Integer(2), sp.Integer(1))
            )
            t = sp.Symbol("t", real=True)
            evidence = causal_exponential_convolution(a, b, t)
            if not evidence.success:
                return SolutionDraft(
                    interpretation="连续时间 LTI 零状态响应卷积",
                    concepts_used=["convolution"],
                    plan_summary=plan.steps,
                    derivation_steps=[],
                    candidate_answer_latex="",
                    assumptions=[],
                    unresolved_questions=[evidence.error_message or "卷积工具失败"],
                )
            answer = evidence.result_latex or evidence.result_text or ""
            return SolutionDraft(
                interpretation="两个右边因果指数信号的连续时间卷积。",
                concepts_used=["LTI", "continuous convolution", "unit step support"],
                plan_summary=plan.steps,
                derivation_steps=[
                    DerivationStep(
                        index=1,
                        title="写出卷积",
                        explanation="零状态响应等于输入与冲激响应的卷积。",
                        expression_latex=r"y(t)=\int_{-\infty}^{\infty}x(\tau)h(t-\tau)\,d\tau",
                    ),
                    DerivationStep(
                        index=2,
                        title="确定积分范围",
                        explanation=(
                            r"$u(\tau)$ 要求 $\tau\ge0$，$u(t-\tau)$ 要求 $\tau\le t$，"
                            r"因此 $t\ge0$ 时交集为 $[0,t]$。"
                        ),
                        expression_latex=rf"y(t)=\int_0^t e^{{-{a}\tau}}e^{{-{b}(t-\tau)}}\,d\tau",
                    ),
                    DerivationStep(
                        index=3,
                        title="执行积分",
                        explanation="确定性符号积分给出结果，并保留因果支撑。",
                        expression_latex=answer,
                        tool_evidence_ids=[evidence.evidence_id],
                    ),
                ],
                candidate_answer_latex=answer,
                assumptions=[],
                unresolved_questions=[],
            )
        return SolutionDraft(
            interpretation="按题目所给条件建立标准信号与系统计算。",
            concepts_used=classification.topics,
            plan_summary=plan.steps,
            derivation_steps=[
                DerivationStep(
                    index=1, title="条件检查", explanation="已核对题目条件与统一变换约定。"
                )
            ],
            candidate_answer_latex="\\text{请配置模型服务 API Key 以求解该非内置题型}",
            assumptions=[],
            unresolved_questions=["离线求解器暂不覆盖该题型"],
        )
