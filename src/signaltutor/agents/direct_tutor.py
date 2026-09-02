from __future__ import annotations

import asyncio
from typing import Literal

from pydantic import BaseModel, Field

from signaltutor.agents.model_adapter import StructuredModel
from signaltutor.config.settings import Settings
from signaltutor.prompts import load_prompt


class DirectTutorOutput(BaseModel):
    answer_markdown: str = Field(min_length=1)
    recognized_question: str | None = None
    response_kind: Literal["solve", "review_student_work", "practice"] = "solve"
    chapter: str = "signals"
    topics: list[str] = Field(default_factory=list)
    exam_points: list[str] = Field(default_factory=list)
    common_mistakes: list[str] = Field(default_factory=list)
    score: float | None = Field(default=None, ge=0, le=100)
    first_wrong_step: int | None = Field(default=None, ge=1)
    error_code: str | None = None
    correction_summary: str | None = None
    confidence: float = Field(ge=0, le=1)
    needs_clarification: bool = False
    clarification: str | None = None


class DirectTutor:
    def __init__(self, model: StructuredModel | None, settings: Settings) -> None:
        self.model = model
        self.settings = settings

    async def answer(
        self,
        question: str,
        *,
        mode: Literal["solve", "review_student_work", "practice"] = "solve",
        answer_style: Literal["detailed", "concise", "hint"] = "detailed",
        history: list[dict[str, str]] | None = None,
        reference_question: str | None = None,
        learner_context: str | None = None,
        chapter: str | None = None,
        topics: list[str] | None = None,
        image_bytes: bytes | None = None,
        image_mime: str | None = None,
    ) -> DirectTutorOutput:
        if not self.model or not self.settings.model_enabled:
            return DirectTutorOutput(
                answer_markdown="尚未配置模型服务 API Key，暂时无法回答。",
                recognized_question=question or None,
                response_kind=mode,
                confidence=0,
                needs_clarification=True,
                clarification="请先配置 DASHSCOPE_API_KEY。",
            )
        try:
            async with asyncio.timeout(self.settings.model_request_timeout_seconds):
                generate = getattr(self.model, "generate_once", self.model.generate)
                return await generate(
                    name="SignalTutor Direct Tutor",
                    model=self.settings.models.chat_model,
                    instructions=load_prompt("direct_tutor"),
                    payload={
                        "question": question or "请识别并解答图片中的《信号与系统》题目。",
                        "mode": mode,
                        "conversation_history": history or [],
                        "reference_question": reference_question,
                        "learner_context": learner_context,
                        "requested_chapter": chapter,
                        "requested_topics": topics or [],
                        "answer_style": answer_style,
                    },
                    output_type=DirectTutorOutput,
                    image_bytes=image_bytes,
                    image_mime=image_mime,
                )
        except TimeoutError:
            return DirectTutorOutput(
                answer_markdown="这次模型响应超时，请重新发送。你的题目和图片仍然保留在当前对话中。",
                recognized_question=reference_question or question or None,
                response_kind=mode,
                confidence=0,
                needs_clarification=True,
                clarification="模型服务暂时没有在规定时间内返回结果。",
            )
        except Exception:
            return DirectTutorOutput(
                answer_markdown="暂时无法连接模型服务，请稍后重新发送。你的题目和图片仍然保留在当前对话中。",
                recognized_question=reference_question or question or None,
                response_kind=mode,
                confidence=0,
                needs_clarification=True,
                clarification="模型服务连接失败。",
            )
