from __future__ import annotations

from signaltutor.agents.model_adapter import StructuredModel
from signaltutor.config.settings import Settings
from signaltutor.math.conventions import DEFAULT_CONVENTION
from signaltutor.prompts import load_prompt
from signaltutor.schemas.classification import ProblemClassification
from signaltutor.schemas.problem import ProblemParse
from signaltutor.schemas.retrieval import RetrievalContext
from signaltutor.schemas.solution import SolutionPlan
from signaltutor.schemas.student import AnswerMode


class SolutionPlanner:
    def __init__(self, model: StructuredModel | None, settings: Settings) -> None:
        self.model = model
        self.settings = settings

    async def plan(
        self,
        problem: ProblemParse,
        classification: ProblemClassification,
        retrieval: RetrievalContext,
        mode: AnswerMode,
    ) -> SolutionPlan:
        if not self.model or not self.settings.model_enabled:
            missing_roc = (
                classification.chapter == "z_transform"
                and "roc" not in problem.question_text.lower()
                and "收敛域" not in problem.question_text
                and "因果" not in problem.question_text
                and "稳定" not in problem.question_text
            )
            if mode == "review_student_work" or problem.contains_student_work:
                return SolutionPlan(
                    strategy_name="定位学生最早错误",
                    concepts_used=["LTI", "变换域关系"],
                    steps=["逐步核对关系式", "指出首个错误", "给出最短修正"],
                    tool_plan=[],
                    assumptions=[],
                    ambiguity_blockers=[],
                )
            return SolutionPlan(
                strategy_name="卷积直接积分"
                if classification.chapter == "lti"
                else "按变换定义求解",
                concepts_used=classification.topics,
                steps=(
                    ["写出卷积定义", "由阶跃支撑确定积分区间", "积分并保留支撑", "代回校验"]
                    if classification.chapter == "lti"
                    else ["识别数学对象", "应用定义或变换对", "检查题目条件"]
                ),
                tool_plan=classification.required_tools,
                assumptions=[],
                ambiguity_blockers=(
                    ["缺少 ROC 或因果性/稳定性等足以唯一确定时域序列的条件"] if missing_roc else []
                ),
            )
        return await self.model.generate(
            name="SignalTutor Planner",
            model=self.settings.models.solver_model,
            instructions=load_prompt("planner"),
            payload={
                "problem": problem.model_dump(),
                "classification": classification.model_dump(),
                "retrieval": retrieval.model_dump(),
                "convention": DEFAULT_CONVENTION.model_dump(),
                "mode": mode,
            },
            output_type=SolutionPlan,
        )
