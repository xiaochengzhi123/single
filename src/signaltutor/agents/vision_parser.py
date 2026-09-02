from __future__ import annotations

from signaltutor.agents.model_adapter import StructuredModel
from signaltutor.config.settings import Settings
from signaltutor.prompts import load_prompt
from signaltutor.schemas.problem import ProblemParse


class VisionProblemParser:
    def __init__(self, model: StructuredModel, settings: Settings) -> None:
        self.model = model
        self.settings = settings

    async def parse(self, image: bytes, mime: str, context: str | None = None) -> ProblemParse:
        return await self.model.generate(
            name="SignalTutor ParseImage",
            model=self.settings.models.vision_model,
            instructions=load_prompt("vision_parser"),
            payload={"context": context or "请忠实解析图片"},
            output_type=ProblemParse,
            image_bytes=image,
            image_mime=mime,
        )
