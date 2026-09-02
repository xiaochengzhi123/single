from __future__ import annotations

from signaltutor.agents.model_adapter import StructuredModel
from signaltutor.config.settings import Settings
from signaltutor.math.conventions import DEFAULT_CONVENTION
from signaltutor.prompts import load_prompt
from signaltutor.schemas.classification import ProblemClassification
from signaltutor.schemas.problem import ProblemParse
from signaltutor.schemas.retrieval import RetrievalContext
from signaltutor.schemas.solution import SolutionDraft, SolutionPlan
from signaltutor.schemas.verification import VerificationResult
from signaltutor.tools.verification import deterministic_rule_check


class Verifier:
    def __init__(self, model: StructuredModel | None, settings: Settings) -> None:
        self.model = model
        self.settings = settings

    async def verify(
        self,
        problem: ProblemParse,
        classification: ProblemClassification,
        retrieval: RetrievalContext,
        plan: SolutionPlan,
        solution: SolutionDraft,
    ) -> VerificationResult:
        rules = deterministic_rule_check(problem, classification, solution)
        if not self.model or not self.settings.model_enabled or not rules.is_correct:
            if rules.is_correct and solution.unresolved_questions:
                rules.is_correct = False
                rules.confidence = 0.95
            if rules.is_correct:
                rules.symbolic_check = bool(solution.derivation_steps)
                rules.confidence = 0.98
            return rules
        return await self.model.generate(
            name="SignalTutor Verifier",
            model=self.settings.models.verifier_model,
            instructions=load_prompt("verifier"),
            payload={
                "problem": problem.model_dump(),
                "classification": classification.model_dump(),
                "retrieval": retrieval.model_dump(),
                "plan": plan.model_dump(),
                "solution": solution.model_dump(),
                "deterministic_rules": rules.model_dump(),
                "convention": DEFAULT_CONVENTION.model_dump(),
            },
            output_type=VerificationResult,
        )
