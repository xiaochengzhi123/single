import pytest

from signaltutor.students.repository import PersistentStudentRepository


async def test_learning_store_survives_repository_recreation(tmp_path) -> None:
    path = tmp_path / "learning.json"
    first = PersistentStudentRepository(path)
    await first.save_mistake(
        student_id="student-a",
        problem_id="problem-a",
        question="为什么 Z 变换需要 ROC？",
        answer_markdown="因为 ROC 与序列支撑有关。",
        chapter="z_transform",
        topics=["roc"],
        common_mistakes=["默认因果"],
    )
    await first.record_attempt("student-a", ["z_transform/roc"], 0.4, [])

    second = PersistentStudentRepository(path)
    overview = await second.get_overview("student-a")

    assert overview["open_mistakes"] == 1
    assert overview["mistakes"][0]["question"] == "为什么 Z 变换需要 ROC？"
    assert overview["topics"][0]["mastery"] == pytest.approx(0.48)
