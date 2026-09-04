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


async def test_mistake_keeps_complete_source_and_hides_internal_image_key(tmp_path) -> None:
    repository = PersistentStudentRepository(tmp_path / "learning.json")
    saved = await repository.save_mistake(
        student_id="student-image",
        problem_id="problem-image",
        question="完整图片题目：求系统的单位冲激响应。",
        answer_markdown="先求系统函数，再作反变换。",
        chapter="lti",
        topics=["impulse_response"],
        common_mistakes=["遗漏初始条件"],
        source_type="uploaded_image",
        image_key="asset.png",
    )

    overview = await repository.get_overview("student-image")

    assert saved["image_key"] == "asset.png"
    assert overview["mistakes"][0]["question"].startswith("完整图片题目")
    assert overview["mistakes"][0]["answer_markdown"].startswith("先求系统函数")
    assert overview["mistakes"][0]["source_type"] == "uploaded_image"
    assert overview["mistakes"][0]["has_image"] is True
    assert "image_key" not in overview["mistakes"][0]
