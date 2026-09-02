from __future__ import annotations

from pydantic import BaseModel

from signaltutor.agents.model_adapter import StructuredModel
from signaltutor.config.settings import Settings
from signaltutor.prompts import load_prompt
from signaltutor.schemas.classification import ProblemClassification
from signaltutor.schemas.problem import ProblemParse
from signaltutor.schemas.retrieval import RetrievalContext
from signaltutor.schemas.solution import SolutionDraft
from signaltutor.schemas.student import AnswerMode
from signaltutor.schemas.verification import VerificationResult


class TutorOutput(BaseModel):
    answer_markdown: str


class TutorRenderer:
    def __init__(self, model: StructuredModel | None, settings: Settings) -> None:
        self.model = model
        self.settings = settings

    async def render(
        self,
        problem: ProblemParse,
        classification: ProblemClassification,
        retrieval: RetrievalContext,
        solution: SolutionDraft,
        verification: VerificationResult,
        mode: AnswerMode,
    ) -> str:
        if not verification.is_correct:
            issue = verification.issues[0] if verification.issues else None
            if issue and issue.code == "missing_roc":
                return (
                    "题目信息不足：仅给出有理式 $X(z)$ 不能唯一确定 $x[n]$。"
                    "请补充 ROC，或说明序列是否因果/稳定。"
                    "不同 ROC 会对应不同的右边、左边或双边序列。"
                )
            if issue and issue.code == "wrong_frequency_domain_operation":
                return (
                    "你前面的设定可以继续保留，但最早错误出现在频域关系式："
                    "LTI 零状态响应满足 $Y(s)=X(s)H(s)$，因为时域卷积对应变换域乘法。"
                    "把这一行改正后，再继续做部分分式或逆变换即可。"
                )
            return "当前草稿未通过校验，暂不输出未经验证的结论。"
        if mode == "hint":
            return (
                "先只看两个单位阶跃：$u(\\tau)$ 与 $u(t-\\tau)$ 分别对 "
                "$\\tau$ 给出什么限制？把两个范围取交集，就是卷积积分上下限。"
            )
        if mode == "guided":
            return (
                "我们先走一步：由 $u(\\tau)$ 可知 $\\tau\\ge 0$。"
                "那么 $u(t-\\tau)$ 对 $\\tau$ 的限制是什么？"
            )
        if mode == "review_student_work":
            step = solution.derivation_steps[0]
            return (
                f"最早需要修正的是第 {step.index} 步。{step.explanation} "
                f"正确关系是 ${solution.candidate_answer_latex}$。"
                "此前不涉及这一关系的步骤仍可保留。"
            )
        if self.model and self.settings.model_enabled:
            output = await self.model.generate(
                name="SignalTutor Tutor",
                model=self.settings.models.tutor_model,
                instructions=load_prompt("tutor"),
                payload={
                    "problem": problem.model_dump(),
                    "classification": classification.model_dump(),
                    "retrieval": retrieval.model_dump(),
                    "solution": solution.model_dump(),
                    "verification": verification.model_dump(),
                    "mode": mode,
                },
                output_type=TutorOutput,
            )
            return output.answer_markdown
        concepts = "、".join(classification.topics)
        derivation = "\n\n".join(
            f"{step.index}. {step.title}：{step.explanation}"
            + (f"\n   $${step.expression_latex}$$" if step.expression_latex else "")
            for step in solution.derivation_steps
        )
        return (
            f"【考察知识点】\n\n{concepts}\n\n"
            f"【解题思路】\n\n{solution.interpretation}\n\n"
            f"【详细推导】\n\n{derivation}\n\n"
            f"【最终答案】\n\n$${solution.candidate_answer_latex}$$\n\n"
            "【容易错在哪里】\n\n不要忽略两个单位阶跃共同决定的积分区间，也不要漏写结果的因果支撑。\n\n"
            "【考场技巧】\n\n先画出关于积分变量的支撑范围，再动手积分，通常能避免上下限错误。"
        )
