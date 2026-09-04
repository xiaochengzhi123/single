from __future__ import annotations

import asyncio
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from signaltutor.schemas.knowledge import (
    KnowledgeCitation,
    KnowledgeEntry,
    KnowledgeEntryCreate,
    KnowledgeEntryUpdate,
)


def _tokens(value: str) -> set[str]:
    normalized = value.lower()
    tokens = set(re.findall(r"[a-z0-9_]+", normalized))
    for block in re.findall(r"[\u4e00-\u9fff]+", normalized):
        tokens.update(block)
        tokens.update(block[index : index + 2] for index in range(len(block) - 1))
    return {token for token in tokens if token.strip()}


def _clean_topics(topics: list[str]) -> list[str]:
    return list(dict.fromkeys(topic.strip() for topic in topics if topic.strip()))[:20]


class PersistentKnowledgeRepository:
    """Single-process JSON knowledge store used by the current Railway deployment."""

    def __init__(self, path: Path, seed_dir: Path = Path("knowledge/seed")) -> None:
        self.path = path
        self.seed_dir = seed_dir
        self._lock = asyncio.Lock()

    def _seed_entries(self) -> list[KnowledgeEntry]:
        entries: list[KnowledgeEntry] = []
        now = datetime.now(UTC)

        def rows(filename: str) -> list[dict]:
            path = self.seed_dir / filename
            if not path.exists():
                return []
            return [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line
            ]

        for row in rows("concepts.jsonl"):
            content = "\n\n".join(
                part
                for part in [row.get("definition"), row.get("formula"), row.get("intuition")]
                if part
            )
            entries.append(
                KnowledgeEntry(
                    id=f"seed_concept_{row['id']}",
                    title=row["title"],
                    content=content,
                    kind="formula" if row.get("formula") else "textbook",
                    chapter=row["chapter"],
                    topics=[row["topic"]],
                    source_url=None,
                    created_at=now,
                )
            )
        for row in rows("solution_patterns.jsonl"):
            content = row["when_to_use"] + "\n\n标准步骤：\n" + "\n".join(
                f"{index}. {step}" for index, step in enumerate(row["steps"], start=1)
            )
            entries.append(
                KnowledgeEntry(
                    id=f"seed_pattern_{row['id']}",
                    title=row["name"],
                    content=content,
                    kind="solution",
                    chapter=row["chapter"],
                    topics=row.get("topics", []),
                    created_at=now,
                )
            )
        for row in rows("sample_problems.jsonl"):
            content = f"题目：\n{row['question']}\n\n参考解答：\n{row['solution']}"
            entries.append(
                KnowledgeEntry(
                    id=f"seed_problem_{row['id']}",
                    title=f"示例题 {row['id']}",
                    content=content,
                    kind="past_exam" if row.get("school") else "solution",
                    school=row.get("school"),
                    year=row.get("year"),
                    chapter=row["chapter"],
                    topics=row.get("topics", []),
                    difficulty=row.get("difficulty"),
                    created_at=now,
                )
            )
        return entries

    def _read(self) -> list[KnowledgeEntry]:
        if not self.path.exists():
            return self._seed_entries()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return [KnowledgeEntry.model_validate(row) for row in data.get("entries", [])]
        except (OSError, json.JSONDecodeError, ValueError):
            return self._seed_entries()

    def _write(self, entries: list[KnowledgeEntry]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        payload = {"entries": [entry.model_dump(mode="json") for entry in entries]}
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)
        self.path.chmod(0o600)

    async def list_entries(self, *, include_unpublished: bool = False) -> list[KnowledgeEntry]:
        async with self._lock:
            entries = self._read()
        if not include_unpublished:
            entries = [entry for entry in entries if entry.published]
        return sorted(entries, key=lambda entry: entry.created_at, reverse=True)

    async def create(self, value: KnowledgeEntryCreate) -> KnowledgeEntry:
        created = (await self.create_many([value]))[0]
        return created

    async def create_many(self, values: list[KnowledgeEntryCreate]) -> list[KnowledgeEntry]:
        created = [
            KnowledgeEntry(
                id=f"kb_{uuid4().hex}",
                **value.model_copy(update={"topics": _clean_topics(value.topics)}).model_dump(),
            )
            for value in values
        ]
        async with self._lock:
            entries = self._read()
            entries.extend(created)
            self._write(entries)
        return created

    async def update(
        self, entry_id: str, value: KnowledgeEntryUpdate
    ) -> KnowledgeEntry | None:
        async with self._lock:
            entries = self._read()
            for index, entry in enumerate(entries):
                if entry.id != entry_id:
                    continue
                changes = value.model_dump(exclude_unset=True)
                if "topics" in changes and changes["topics"] is not None:
                    changes["topics"] = _clean_topics(changes["topics"])
                updated = entry.model_copy(update=changes)
                entries[index] = updated
                self._write(entries)
                return updated
        return None

    async def delete(self, entry_id: str) -> bool:
        async with self._lock:
            entries = self._read()
            remaining = [entry for entry in entries if entry.id != entry_id]
            if len(remaining) == len(entries):
                return False
            self._write(remaining)
            return True

    async def get(
        self, entry_id: str, *, include_unpublished: bool = False
    ) -> KnowledgeEntry | None:
        entries = await self.list_entries(include_unpublished=include_unpublished)
        return next((entry for entry in entries if entry.id == entry_id), None)

    async def schools(self) -> list[str]:
        entries = await self.list_entries()
        return sorted({entry.school for entry in entries if entry.school})

    async def search(
        self,
        question: str,
        *,
        school: str | None = None,
        chapter: str | None = None,
        topics: list[str] | None = None,
        top_k: int = 6,
    ) -> list[KnowledgeEntry]:
        query_tokens = _tokens(" ".join([question, chapter or "", *(topics or [])]))
        entries = await self.list_entries()
        selected_school = (school or "").strip().lower()

        def score(entry: KnowledgeEntry) -> float:
            entry_school = (entry.school or "").strip().lower()
            if selected_school and entry_school and entry_school != selected_school:
                return -1
            title_tokens = _tokens(entry.title)
            body_tokens = _tokens(
                " ".join([entry.content, entry.chapter, *entry.topics, entry.school or ""])
            )
            value = len(query_tokens & body_tokens) + 2.5 * len(query_tokens & title_tokens)
            if chapter and entry.chapter == chapter:
                value += 5
            value += 3 * len(set(topics or []) & set(entry.topics))
            if query_tokens and value <= 0:
                return 0
            if selected_school and entry_school == selected_school:
                value += 8
            if question.strip() and question.strip().lower() in entry.content.lower():
                value += 6
            return value

        ranked = sorted(entries, key=score, reverse=True)
        return [entry for entry in ranked if score(entry) > 0][: max(1, min(top_k, 12))]

    @staticmethod
    def citations(entries: list[KnowledgeEntry]) -> list[KnowledgeCitation]:
        return [
            KnowledgeCitation(
                entry_id=entry.id,
                title=entry.title,
                kind=entry.kind,
                school=entry.school,
                year=entry.year,
                source_page=entry.source_page,
                source_url=entry.source_url,
                excerpt=(entry.content[:180] + "…") if len(entry.content) > 180 else entry.content,
            )
            for entry in entries
        ]
