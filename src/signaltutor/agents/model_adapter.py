from __future__ import annotations

import base64
import json
import re
from collections.abc import AsyncIterator
from typing import Any, Literal, Protocol, TypeVar, cast

from pydantic import BaseModel

from signaltutor.config.settings import Settings

SchemaT = TypeVar("SchemaT", bound=BaseModel)


def _partial_json_string_field(value: str, field: str) -> str:
    """Decode the available part of a JSON string without waiting for closing JSON."""
    match = re.search(rf'"{re.escape(field)}"\s*:\s*"', value)
    if not match:
        return ""
    cursor = match.end()
    decoded: list[str] = []
    escapes = {
        "\"": "\"",
        "\\": "\\",
        "/": "/",
        "b": "\b",
        "f": "\f",
        "n": "\n",
        "r": "\r",
        "t": "\t",
    }
    while cursor < len(value):
        char = value[cursor]
        if char == '"':
            break
        if char != "\\":
            decoded.append(char)
            cursor += 1
            continue
        if cursor + 1 >= len(value):
            break
        escaped = value[cursor + 1]
        if escaped == "u":
            digits = value[cursor + 2 : cursor + 6]
            if len(digits) < 4:
                break
            try:
                decoded.append(chr(int(digits, 16)))
            except ValueError:
                pass
            cursor += 6
            continue
        decoded.append(escapes.get(escaped, escaped))
        cursor += 2
    return "".join(decoded)


class StructuredModel(Protocol):
    async def generate(
        self,
        *,
        name: str,
        model: str,
        instructions: str,
        payload: dict[str, Any],
        output_type: type[SchemaT],
        image_bytes: bytes | None = None,
        image_mime: str | None = None,
    ) -> SchemaT: ...


class QwenAgentsSDKModel:
    """Qwen model boundary implemented through DashScope's OpenAI-compatible API."""

    def __init__(self, settings: Settings) -> None:
        from openai import AsyncOpenAI

        if not settings.dashscope_api_key:
            raise ValueError("DASHSCOPE_API_KEY is required when Qwen model mode is enabled")
        self.settings = settings
        self.client = AsyncOpenAI(
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
            timeout=settings.model_request_timeout_seconds,
            max_retries=1,
        )

    async def generate_once(
        self,
        *,
        name: str,
        model: str,
        instructions: str,
        payload: dict[str, Any],
        output_type: type[SchemaT],
        image_bytes: bytes | None = None,
        image_mime: str | None = None,
    ) -> SchemaT:
        """Single DashScope request for latency-sensitive chat interactions."""
        schema = json.dumps(output_type.model_json_schema(), ensure_ascii=False)
        system_prompt = (
            f"{instructions}\n\n"
            "必须只输出一个合法 JSON 对象，不要使用 Markdown 代码围栏。"
            f"JSON 必须符合以下 schema：{schema}"
        )
        content: list[dict[str, Any]] = [
            {"type": "text", "text": json.dumps(payload, ensure_ascii=False, default=str)}
        ]
        if image_bytes is not None:
            mime = image_mime or "image/png"
            encoded = base64.b64encode(image_bytes).decode("ascii")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime};base64,{encoded}",
                        "detail": "high",
                    },
                }
            )
        response = await self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=4096,
            extra_body={"enable_thinking": False},
        )
        raw = response.choices[0].message.content or "{}"
        parsed = json.loads(raw)
        if "answer_markdown" in output_type.model_fields and "answer_markdown" not in parsed:
            for alternative in ("answer_mark", "answer", "content"):
                if parsed.get(alternative):
                    parsed["answer_markdown"] = parsed[alternative]
                    break
        return output_type.model_validate(parsed)

    async def stream_once(
        self,
        *,
        name: str,
        model: str,
        instructions: str,
        payload: dict[str, Any],
        output_type: type[SchemaT],
        image_bytes: bytes | None = None,
        image_mime: str | None = None,
    ) -> AsyncIterator[tuple[Literal["delta", "done"], str | SchemaT]]:
        schema = json.dumps(output_type.model_json_schema(), ensure_ascii=False)
        system_prompt = (
            f"{instructions}\n\n"
            "必须只输出一个合法 JSON 对象，不要使用 Markdown 代码围栏。"
            "必须首先输出 answer_markdown 字段，再输出其他字段。"
            f"JSON 必须符合以下 schema：{schema}"
        )
        content: list[dict[str, Any]] = [
            {"type": "text", "text": json.dumps(payload, ensure_ascii=False, default=str)}
        ]
        if image_bytes is not None:
            mime = image_mime or "image/png"
            encoded = base64.b64encode(image_bytes).decode("ascii")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime};base64,{encoded}",
                        "detail": "high",
                    },
                }
            )
        stream = await self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=4096,
            extra_body={"enable_thinking": False},
            stream=True,
        )
        raw = ""
        visible = ""
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content or ""
            if not delta:
                continue
            raw += delta
            next_visible = _partial_json_string_field(raw, "answer_markdown")
            if len(next_visible) > len(visible):
                yield "delta", next_visible[len(visible) :]
                visible = next_visible
        parsed = json.loads(raw or "{}")
        if "answer_markdown" in output_type.model_fields and "answer_markdown" not in parsed:
            for alternative in ("answer_mark", "answer", "content"):
                if parsed.get(alternative):
                    parsed["answer_markdown"] = parsed[alternative]
                    break
        yield "done", output_type.model_validate(parsed)

    async def generate(
        self,
        *,
        name: str,
        model: str,
        instructions: str,
        payload: dict[str, Any],
        output_type: type[SchemaT],
        image_bytes: bytes | None = None,
        image_mime: str | None = None,
    ) -> SchemaT:
        from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled

        set_tracing_disabled(self.settings.agents_disable_tracing)
        qwen_model = OpenAIChatCompletionsModel(model=model, openai_client=self.client)
        agent = Agent(
            name=name,
            model=qwen_model,
            instructions=instructions,
            output_type=output_type,
        )
        content: list[dict[str, Any]] = [
            {"type": "input_text", "text": json.dumps(payload, ensure_ascii=False, default=str)}
        ]
        if image_bytes is not None:
            mime = image_mime or "image/png"
            encoded = base64.b64encode(image_bytes).decode("ascii")
            content.append(
                {
                    "type": "input_image",
                    "image_url": f"data:{mime};base64,{encoded}",
                    "detail": "high",
                }
            )
        agent_input = cast(Any, [{"role": "user", "content": content}])
        result = await Runner.run(agent, input=agent_input)
        final = result.final_output
        if isinstance(final, output_type):
            return final
        return output_type.model_validate(final)
