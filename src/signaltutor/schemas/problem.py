from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FormulaItem(BaseModel):
    raw: str | None = None
    latex: str
    confidence: float = Field(ge=0, le=1)


class UncertainElement(BaseModel):
    description: str
    location: str | None = None
    candidates: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class FigureInfo(BaseModel):
    type: Literal["signal_plot", "block_diagram", "pole_zero_plot", "spectrum", "other"]
    description: str
    extracted_points: list[list[float]] | None = None


class StudentWorkStep(BaseModel):
    step_number: int
    raw_expression: str | None = None
    normalized_latex: str | None = None
    description: str | None = None


class ProblemParse(BaseModel):
    input_type: Literal["text", "image", "text_image"]
    question_text: str
    known_conditions: list[str] = Field(default_factory=list)
    target: str
    formulas: list[FormulaItem] = Field(default_factory=list)
    figures: list[FigureInfo] = Field(default_factory=list)
    uncertain_elements: list[UncertainElement] = Field(default_factory=list)
    contains_student_work: bool = False
    student_steps: list[StudentWorkStep] = Field(default_factory=list)
    signal_domain: Literal["continuous_time", "discrete_time", "mixed", "unknown"]
    confidence: float = Field(ge=0, le=1)


class TextParseRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20000)
    student_work: str | None = Field(default=None, max_length=20000)
    conversation_id: str | None = None


class ConfirmProblemRequest(BaseModel):
    problem_parse: ProblemParse
