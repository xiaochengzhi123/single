from pydantic import BaseModel, Field


class SolutionPlan(BaseModel):
    strategy_name: str
    concepts_used: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    tool_plan: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    ambiguity_blockers: list[str] = Field(default_factory=list)


class DerivationStep(BaseModel):
    index: int
    title: str
    explanation: str
    expression_latex: str | None = None
    tool_evidence_ids: list[str] = Field(default_factory=list)


class SolutionDraft(BaseModel):
    interpretation: str
    concepts_used: list[str] = Field(default_factory=list)
    plan_summary: list[str] = Field(default_factory=list)
    derivation_steps: list[DerivationStep] = Field(default_factory=list)
    candidate_answer_latex: str
    assumptions: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
