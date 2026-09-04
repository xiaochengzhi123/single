from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from signaltutor.schemas.student import MasteryRecord
from signaltutor.students.mastery import update_mastery


def _now() -> str:
    return datetime.now(UTC).isoformat()


class PersistentStudentRepository:
    """Small local learning store used until account-backed persistence is enabled."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = asyncio.Lock()

    def _read(self) -> dict:
        if not self.path.exists():
            return {"mastery": {}, "errors": {}, "mistakes": []}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"mastery": {}, "errors": {}, "mistakes": []}
        data.setdefault("mastery", {})
        data.setdefault("errors", {})
        data.setdefault("mistakes", [])
        return data

    def _write(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    async def record_attempt(
        self,
        student_id: str,
        topics: list[str],
        score: float,
        issues: list[dict],
    ) -> None:
        async with self._lock:
            data = self._read()
            student = data["mastery"].setdefault(student_id, {})
            for topic in topics:
                previous = student.get(topic, {})
                attempts = int(previous.get("attempts", 0)) + 1
                correct_attempts = int(previous.get("correct_attempts", 0)) + int(score >= 0.8)
                student[topic] = {
                    "topic": topic,
                    "mastery": update_mastery(float(previous.get("mastery", 0.5)), score),
                    "attempts": attempts,
                    "correct_attempts": correct_attempts,
                    "last_seen_at": _now(),
                }
            if issues:
                error_rows = data["errors"].setdefault(student_id, [])
                default_topic = topics[0] if topics else "signals/basic_operations"
                for issue in issues:
                    error_rows.append(
                        {
                            **issue,
                            "topic": issue.get("topic", default_topic),
                            "created_at": _now(),
                        }
                    )
            self._write(data)

    async def get_mastery(self, student_id: str) -> list[MasteryRecord]:
        async with self._lock:
            rows = self._read()["mastery"].get(student_id, {})
            return [MasteryRecord.model_validate(row) for row in rows.values()]

    async def get_errors(self, student_id: str) -> list[dict]:
        async with self._lock:
            return list(self._read()["errors"].get(student_id, []))

    async def save_mistake(
        self,
        *,
        student_id: str,
        problem_id: str | None,
        question: str,
        answer_markdown: str,
        chapter: str,
        topics: list[str],
        common_mistakes: list[str],
        source_type: str = "text",
        image_key: str | None = None,
    ) -> dict:
        async with self._lock:
            data = self._read()
            existing = next(
                (
                    row
                    for row in data["mistakes"]
                    if row["student_id"] == student_id
                    and (
                        (problem_id and row.get("problem_id") == problem_id)
                        or row["question"].strip() == question.strip()
                    )
                ),
                None,
            )
            if existing:
                # Enrich records created by older versions instead of leaving a
                # permanently truncated question or a missing uploaded image.
                existing.update(
                    {
                        "problem_id": problem_id or existing.get("problem_id"),
                        "question": question,
                        "answer_markdown": answer_markdown or existing.get("answer_markdown", ""),
                        "chapter": chapter,
                        "topics": topics,
                        "common_mistakes": common_mistakes,
                        "source_type": source_type,
                        "image_key": image_key or existing.get("image_key"),
                    }
                )
                self._write(data)
                return existing
            row = {
                "id": str(uuid4()),
                "student_id": student_id,
                "problem_id": problem_id,
                "question": question,
                "answer_markdown": answer_markdown,
                "source_type": source_type,
                "image_key": image_key,
                "chapter": chapter,
                "topics": topics,
                "common_mistakes": common_mistakes,
                "mastered": False,
                "created_at": _now(),
            }
            data["mistakes"].append(row)
            self._write(data)
            return row

    async def list_mistakes(self, student_id: str) -> list[dict]:
        async with self._lock:
            rows = [
                row for row in self._read()["mistakes"] if row["student_id"] == student_id
            ]
            normalized = []
            for row in rows:
                item = dict(row)
                item.setdefault("source_type", "text")
                item["has_image"] = bool(item.get("image_key"))
                item.pop("image_key", None)
                normalized.append(item)
            return sorted(normalized, key=lambda row: row["created_at"], reverse=True)

    async def get_mistake(self, student_id: str, mistake_id: str) -> dict | None:
        async with self._lock:
            return next(
                (
                    dict(row)
                    for row in self._read()["mistakes"]
                    if row["id"] == mistake_id and row["student_id"] == student_id
                ),
                None,
            )

    async def set_mistake_mastered(
        self,
        student_id: str,
        mistake_id: str,
        mastered: bool,
    ) -> dict | None:
        async with self._lock:
            data = self._read()
            for row in data["mistakes"]:
                if row["id"] == mistake_id and row["student_id"] == student_id:
                    row["mastered"] = mastered
                    self._write(data)
                    return row
            return None

    async def get_overview(self, student_id: str) -> dict:
        mastery = await self.get_mastery(student_id)
        mistakes = await self.list_mistakes(student_id)
        topics = sorted(mastery, key=lambda row: (row.mastery, -row.attempts))
        return {
            "student_id": student_id,
            "topics": [row.model_dump(mode="json") for row in topics],
            "mistakes": mistakes,
            "open_mistakes": sum(not row["mastered"] for row in mistakes),
        }
