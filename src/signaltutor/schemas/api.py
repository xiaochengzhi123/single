from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from signaltutor.schemas.classification import ProblemClassification
from signaltutor.schemas.knowledge import KnowledgeCitation
from signaltutor.schemas.problem import ProblemParse
from signaltutor.schemas.solution import SolutionDraft, SolutionPlan
from signaltutor.schemas.student import AnswerMode
from signaltutor.schemas.verification import VerificationResult

STUDENT_ID_PATTERN = r"^[A-Za-z0-9_-]+$"
StudentId = Annotated[
    str,
    Field(min_length=1, max_length=128, pattern=STUDENT_ID_PATTERN),
]


class SolveProblemRequest(BaseModel):
    mode: AnswerMode = "full_solution"
    confirmed_problem: ProblemParse | None = None
    student_id: StudentId | None = None
    conversation_id: str | None = None


class DirectSolveRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20000)
    mode: AnswerMode = "full_solution"
    student_work: str | None = None
    conversation_id: str | None = None


class DirectChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class DirectChatAnswerRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20000)
    mode: Literal["solve", "review_student_work"] = "solve"
    answer_style: Literal["detailed", "concise", "hint"] = "detailed"
    history: list[DirectChatHistoryMessage] = Field(default_factory=list, max_length=12)
    reference_question: str | None = Field(default=None, max_length=20000)
    target_school: str | None = Field(default=None, max_length=120)


class DirectChatAnswerResponse(BaseModel):
    problem_id: str
    answer_markdown: str
    recognized_question: str | None = None
    response_kind: Literal["solve", "review_student_work", "practice"] = "solve"
    source_type: Literal["text", "uploaded_image", "ai_generated"] = "text"
    chapter: str = "signals"
    topics: list[str] = Field(default_factory=list)
    exam_points: list[str] = Field(default_factory=list)
    common_mistakes: list[str] = Field(default_factory=list)
    score: float | None = Field(default=None, ge=0, le=100)
    first_wrong_step: int | None = Field(default=None, ge=1)
    error_code: str | None = None
    correction_summary: str | None = None
    confidence: float = Field(ge=0, le=1)
    needs_clarification: bool = False
    clarification: str | None = None
    sources: list[KnowledgeCitation] = Field(default_factory=list)


class PracticeGenerateRequest(BaseModel):
    source_question: str = Field(min_length=1, max_length=20000)
    chapter: str = "signals"
    topics: list[str] = Field(default_factory=list)
    target_school: str | None = Field(default=None, max_length=120)


class MistakeCreateRequest(BaseModel):
    problem_id: str | None = None
    question: str = Field(min_length=1, max_length=20000)
    answer_markdown: str = Field(default="", max_length=50000)
    source_type: Literal["text", "uploaded_image", "ai_generated"] = "text"
    chapter: str = "signals"
    topics: list[str] = Field(default_factory=list)
    common_mistakes: list[str] = Field(default_factory=list)


class MistakeUpdateRequest(BaseModel):
    mastered: bool


class SolveProblemResponse(BaseModel):
    status: Literal["ok", "needs_confirmation", "needs_clarification", "verification_failed"]
    problem_id: str
    problem_parse: ProblemParse
    classification: ProblemClassification | None = None
    plan: SolutionPlan | None = None
    solution: SolutionDraft | None = None
    verification: VerificationResult | None = None
    answer: str | None = None
    clarification: str | None = None
    workflow_events: list[str] = Field(default_factory=list)


class ParseResponse(BaseModel):
    status: Literal["ok", "needs_confirmation"]
    problem_id: str
    problem_parse: ProblemParse


class FeedbackRequest(BaseModel):
    problem_id: str
    rating: Literal["helpful", "not_helpful", "wrong_answer", "wrong_image_parse"]
    comment: str | None = Field(default=None, max_length=2000)
