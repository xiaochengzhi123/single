from __future__ import annotations

import json
import math
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from signaltutor.rag.embeddings import deterministic_embedding
from signaltutor.schemas.retrieval import (
    ErrorPattern,
    KnowledgeCard,
    ProblemExample,
    RetrievalContext,
    RetrievalQuery,
    SolutionPattern,
)

ModelT = TypeVar("ModelT", bound=BaseModel)


class InMemoryKnowledgeRepository:
    def __init__(
        self,
        concepts: list[KnowledgeCard] | None = None,
        patterns: list[SolutionPattern] | None = None,
        errors: list[ErrorPattern] | None = None,
        examples: list[ProblemExample] | None = None,
    ) -> None:
        self.concepts = concepts or []
        self.patterns = patterns or []
        self.errors = errors or []
        self.examples = examples or []

    @classmethod
    def from_seed(cls, seed_dir: Path = Path("knowledge/seed")) -> InMemoryKnowledgeRepository:
        def load(name: str, model: type[ModelT]) -> list[ModelT]:
            path = seed_dir / name
            if not path.exists():
                return []
            return [
                model.model_validate(json.loads(line))
                for line in path.read_text().splitlines()
                if line
            ]

        return cls(
            concepts=load("concepts.jsonl", KnowledgeCard),
            patterns=load("solution_patterns.jsonl", SolutionPattern),
            errors=load("error_patterns.jsonl", ErrorPattern),
            examples=load("sample_problems.jsonl", ProblemExample),
        )

    async def retrieve(self, query: RetrievalQuery, top_k: int = 4) -> RetrievalContext:
        tokens = set(query.question.lower().replace("，", " ").replace("。", " ").split())
        query_vector = deterministic_embedding(query.question)

        def vector_score(text: str) -> int:
            candidate = deterministic_embedding(text)
            similarity = sum(
                left * right for left, right in zip(query_vector, candidate, strict=True)
            )
            if math.isnan(similarity):
                return 0
            return round(similarity * 4)

        def score(chapter: str, topics: list[str], text: str) -> int:
            return (
                (5 if chapter == query.chapter else 0)
                + len(set(topics) & set(query.topics)) * 3
                + sum(1 for token in tokens if token and token in text.lower())
                + vector_score(text)
            )

        concepts = sorted(
            self.concepts,
            key=lambda item: score(item.chapter, [item.topic], item.title + item.definition),
            reverse=True,
        )[:top_k]
        patterns = sorted(
            self.patterns,
            key=lambda item: score(item.chapter, item.topics, item.name + item.when_to_use),
            reverse=True,
        )[:2]
        errors = sorted(
            self.errors,
            key=lambda item: score(item.chapter, item.topics, item.description),
            reverse=True,
        )[:3]
        examples = sorted(
            self.examples,
            key=lambda item: score(item.chapter, item.topics, item.question),
            reverse=True,
        )[:2]
        return RetrievalContext(
            concepts=[
                item for item in concepts if score(item.chapter, [item.topic], item.title) > 0
            ],
            solution_patterns=[
                item for item in patterns if score(item.chapter, item.topics, item.name) > 0
            ],
            error_patterns=[
                item for item in errors if score(item.chapter, item.topics, item.description) > 0
            ],
            similar_problems=[
                item for item in examples if score(item.chapter, item.topics, item.question) > 0
            ],
        )
