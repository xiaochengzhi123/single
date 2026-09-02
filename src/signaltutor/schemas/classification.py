from typing import Literal

from pydantic import BaseModel, Field


class ProblemClassification(BaseModel):
    chapter: str
    topics: list[str] = Field(default_factory=list)
    question_type: Literal[
        "concept", "calculation", "proof", "analysis", "student_work_review", "mixed"
    ]
    difficulty: int = Field(ge=1, le=5)
    required_tools: list[str] = Field(default_factory=list)
    required_checks: list[str] = Field(default_factory=list)
    likely_error_patterns: list[str] = Field(default_factory=list)
