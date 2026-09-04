from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

KnowledgeKind = Literal[
    "past_exam",
    "textbook",
    "formula",
    "syllabus",
    "solution",
    "other",
]


class KnowledgeEntryBase(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    content: str = Field(min_length=1, max_length=50000)
    kind: KnowledgeKind = "other"
    school: str | None = Field(default=None, max_length=120)
    year: int | None = Field(default=None, ge=1980, le=2100)
    chapter: str = Field(default="signals", min_length=1, max_length=80)
    topics: list[str] = Field(default_factory=list, max_length=20)
    difficulty: int | None = Field(default=None, ge=1, le=5)
    source_page: int | None = Field(default=None, ge=1)
    source_url: str | None = Field(default=None, max_length=2000, pattern=r"^https?://")
    published: bool = True


class KnowledgeEntryCreate(KnowledgeEntryBase):
    pass


class KnowledgeEntryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    content: str | None = Field(default=None, min_length=1, max_length=50000)
    kind: KnowledgeKind | None = None
    school: str | None = Field(default=None, max_length=120)
    year: int | None = Field(default=None, ge=1980, le=2100)
    chapter: str | None = Field(default=None, min_length=1, max_length=80)
    topics: list[str] | None = Field(default=None, max_length=20)
    difficulty: int | None = Field(default=None, ge=1, le=5)
    source_page: int | None = Field(default=None, ge=1)
    source_url: str | None = Field(default=None, max_length=2000, pattern=r"^https?://")
    published: bool | None = None


class KnowledgeEntry(KnowledgeEntryBase):
    id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class KnowledgeCitation(BaseModel):
    entry_id: str
    title: str
    kind: KnowledgeKind
    school: str | None = None
    year: int | None = None
    source_page: int | None = None
    source_url: str | None = None
    excerpt: str


class KnowledgeImportResponse(BaseModel):
    imported: int
    entries: list[KnowledgeEntry]
