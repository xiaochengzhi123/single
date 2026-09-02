from __future__ import annotations

from datetime import UTC, datetime

from signaltutor.schemas.student import MasteryRecord


def update_mastery(old_mastery: float, current_score: float, *, alpha: float = 0.2) -> float:
    if not 0 <= alpha <= 1:
        raise ValueError("alpha must be within [0, 1]")
    return min(1.0, max(0.0, alpha * current_score + (1 - alpha) * old_mastery))


class InMemoryStudentRepository:
    def __init__(self) -> None:
        self.mastery: dict[str, dict[str, MasteryRecord]] = {}
        self.errors: dict[str, list[dict]] = {}

    async def record_attempt(
        self, student_id: str, topics: list[str], score: float, issues: list[dict]
    ) -> None:
        student = self.mastery.setdefault(student_id, {})
        for topic in topics:
            old = student.get(topic, MasteryRecord(topic=topic, mastery=0.5))
            student[topic] = MasteryRecord(
                topic=topic,
                mastery=update_mastery(old.mastery, score),
                attempts=old.attempts + 1,
                correct_attempts=old.correct_attempts + int(score >= 0.8),
                last_seen_at=datetime.now(UTC),
            )
        if issues:
            rows = self.errors.setdefault(student_id, [])
            for issue in issues:
                rows.append({**issue, "created_at": datetime.now(UTC).isoformat()})

    async def get_mastery(self, student_id: str) -> list[MasteryRecord]:
        return list(self.mastery.get(student_id, {}).values())

    async def get_errors(self, student_id: str) -> list[dict]:
        return self.errors.get(student_id, [])
