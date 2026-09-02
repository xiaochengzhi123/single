from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from signaltutor.schemas.problem import ProblemParse


@dataclass
class StoredProblem:
    id: str
    parse: ProblemParse
    student_id: str | None = None
    conversation_id: str | None = None
    asset_key: str | None = None


class InMemoryProblemRepository:
    def __init__(self) -> None:
        self.items: dict[str, StoredProblem] = {}
        self.feedback: list[dict] = []

    async def create(
        self,
        problem: ProblemParse,
        *,
        student_id: str | None = None,
        conversation_id: str | None = None,
        asset_key: str | None = None,
    ) -> StoredProblem:
        stored = StoredProblem(str(uuid4()), problem, student_id, conversation_id, asset_key)
        self.items[stored.id] = stored
        return stored

    async def get(self, problem_id: str) -> StoredProblem | None:
        return self.items.get(problem_id)

    async def update_parse(self, problem_id: str, problem: ProblemParse) -> StoredProblem | None:
        stored = self.items.get(problem_id)
        if stored:
            stored.parse = problem
        return stored

    async def add_feedback(self, row: dict) -> None:
        self.feedback.append(row)
