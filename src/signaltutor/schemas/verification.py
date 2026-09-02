from typing import Literal

from pydantic import BaseModel, Field


class VerificationIssue(BaseModel):
    code: str
    severity: Literal["info", "warning", "error"]
    message: str
    related_step: int | None = None


class VerificationResult(BaseModel):
    is_correct: bool
    confidence: float = Field(ge=0, le=1)
    symbolic_check: bool | None = None
    numerical_check: bool | None = None
    transform_domain_check: bool | None = None
    rule_checks_passed: list[str] = Field(default_factory=list)
    issues: list[VerificationIssue] = Field(default_factory=list)
    retry_recommended: bool = False
