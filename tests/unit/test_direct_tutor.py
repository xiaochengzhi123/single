from __future__ import annotations

from typing import Any

from signaltutor.agents.direct_tutor import DirectTutor, DirectTutorOutput
from signaltutor.config.settings import Settings


class RecordingModel:
    def __init__(self) -> None:
        self.call: dict[str, Any] = {}

    async def generate(self, **kwargs: Any) -> DirectTutorOutput:
        self.call = kwargs
        return DirectTutorOutput(
            answer_markdown="该序列是周期序列。",
            recognized_question="判断序列是否周期",
            confidence=0.98,
        )


class FailingModel:
    async def generate(self, **kwargs: Any) -> DirectTutorOutput:
        raise RuntimeError("upstream unavailable")


async def test_direct_tutor_uses_one_chat_model_call_with_image() -> None:
    model = RecordingModel()
    settings = Settings(
        _env_file=None,
        dashscope_api_key="test-key",
        use_fake_models=False,
    )
    tutor = DirectTutor(model, settings)

    result = await tutor.answer(
        "请解答图片中的题目",
        answer_style="hint",
        history=[
            {"role": "user", "content": "判断离散正弦是否周期"},
            {"role": "assistant", "content": "需要检查归一化频率。"},
        ],
        image_bytes=b"image-bytes",
        image_mime="image/png",
    )

    assert result.answer_markdown == "该序列是周期序列。"
    assert model.call["model"] == settings.models.chat_model
    assert model.call["image_bytes"] == b"image-bytes"
    assert model.call["image_mime"] == "image/png"
    assert model.call["payload"]["answer_style"] == "hint"
    assert model.call["payload"]["conversation_history"][0]["role"] == "user"


async def test_direct_tutor_turns_model_failure_into_retryable_answer() -> None:
    settings = Settings(
        _env_file=None,
        dashscope_api_key="test-key",
        use_fake_models=False,
    )
    tutor = DirectTutor(FailingModel(), settings)

    result = await tutor.answer("测试题目")

    assert result.needs_clarification is True
    assert result.confidence == 0
    assert "重新发送" in result.answer_markdown
