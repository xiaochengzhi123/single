from pydantic import BaseModel, Field


class KnowledgeCard(BaseModel):
    id: str
    subject: str = "signals_and_systems"
    chapter: str
    topic: str
    title: str
    definition: str
    formula: str | None = None
    conditions: list[str] = Field(default_factory=list)
    intuition: str | None = None
    common_errors: list[str] = Field(default_factory=list)
    related_topics: list[str] = Field(default_factory=list)
    source: str = "SignalTutor original"
    metadata: dict = Field(default_factory=dict)


class SolutionPattern(BaseModel):
    id: str
    chapter: str
    topics: list[str]
    name: str
    when_to_use: str
    steps: list[str]
    required_checks: list[str] = Field(default_factory=list)
    common_failures: list[str] = Field(default_factory=list)
    example: str | None = None


class ErrorPattern(BaseModel):
    code: str
    chapter: str
    topics: list[str]
    description: str
    symptoms: list[str]
    diagnosis: str
    teaching_feedback: str


class ProblemExample(BaseModel):
    id: str
    school: str | None = None
    year: int | None = None
    chapter: str
    topics: list[str]
    difficulty: int
    question: str
    solution: str
    pitfalls: list[str] = Field(default_factory=list)
    source: str = "SignalTutor original"


class RetrievalQuery(BaseModel):
    chapter: str
    topics: list[str]
    question: str


class RetrievalContext(BaseModel):
    concepts: list[KnowledgeCard] = Field(default_factory=list)
    solution_patterns: list[SolutionPattern] = Field(default_factory=list)
    similar_problems: list[ProblemExample] = Field(default_factory=list)
    error_patterns: list[ErrorPattern] = Field(default_factory=list)
