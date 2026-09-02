from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

AnswerMode = Literal["full_solution", "hint", "guided", "review_student_work"]


class MasteryRecord(BaseModel):
    topic: str
    mastery: float = Field(ge=0, le=1)
    attempts: int = 0
    correct_attempts: int = 0
    last_seen_at: datetime | None = None


class StudentErrorRecord(BaseModel):
    topic: str
    error_code: str
    error_step: int | None = None
    severity: str = "warning"
    created_at: datetime
