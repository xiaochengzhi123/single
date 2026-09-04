import json
from collections.abc import AsyncIterator
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import TypeAdapter, ValidationError

from signaltutor.agents.direct_tutor import DirectTutorOutput
from signaltutor.agents.text_parser import parse_text_problem
from signaltutor.api.auth_dependencies import CurrentUser
from signaltutor.api.dependencies import Services, get_services
from signaltutor.schemas.api import (
    DirectChatAnswerRequest,
    DirectChatAnswerResponse,
    DirectChatHistoryMessage,
    DirectSolveRequest,
    PracticeGenerateRequest,
    SolveProblemRequest,
    SolveProblemResponse,
)
from signaltutor.schemas.knowledge import KnowledgeCitation, KnowledgeEntry
from signaltutor.storage.local import ImageValidationError
from signaltutor.workflows.solve_problem import solve_problem

router = APIRouter(prefix="/api/v1", tags=["chat"])
history_adapter = TypeAdapter(list[DirectChatHistoryMessage])


def _stream_event(event: str, **payload: object) -> bytes:
    return (json.dumps({"type": event, **payload}, ensure_ascii=False) + "\n").encode()


def _parse_history(value: str) -> list[dict[str, str]]:
    try:
        history = history_adapter.validate_json(value)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_history", "message": "对话历史格式无效"},
        ) from exc
    return [item.model_dump() for item in history[-12:]]


async def _learner_context(student_id: str, service: Services) -> str | None:
    overview = await service.students.get_overview(student_id)
    weak_topics = [
        f"{row['topic']}({round(row['mastery'] * 100)}%)"
        for row in overview["topics"][:3]
    ]
    if not weak_topics:
        return None
    return "近期薄弱考点：" + "、".join(weak_topics)


async def _retrieve_knowledge(
    service: Services,
    question: str,
    *,
    target_school: str | None = None,
    chapter: str | None = None,
    topics: list[str] | None = None,
) -> list[KnowledgeEntry]:
    if not question.strip():
        return []
    return await service.knowledge.search(
        question,
        school=target_school,
        chapter=chapter,
        topics=topics,
        top_k=6,
    )


def _knowledge_payload(entries: list[KnowledgeEntry]) -> list[dict[str, object]]:
    return [
        {
            "reference_id": f"资料{index}",
            "title": entry.title,
            "kind": entry.kind,
            "school": entry.school,
            "year": entry.year,
            "chapter": entry.chapter,
            "topics": entry.topics,
            "difficulty": entry.difficulty,
            "source_page": entry.source_page,
            "content": entry.content,
        }
        for index, entry in enumerate(entries, start=1)
    ]


async def _finalize_direct_answer(
    *,
    output: DirectTutorOutput,
    service: Services,
    student_id: str,
    source_question: str,
    asset_key: str | None = None,
    source_type: Literal["text", "uploaded_image", "ai_generated"] = "text",
    sources: list[KnowledgeCitation] | None = None,
) -> DirectChatAnswerResponse:
    if output.response_kind == "review_student_work":
        output = output.model_copy(update={"recognized_question": source_question})
    question = output.recognized_question or source_question
    problem = parse_text_problem(question)
    stored = await service.problems.create(
        problem,
        student_id=student_id,
        asset_key=asset_key,
    )
    if output.response_kind == "review_student_work" and output.score is not None:
        issues = []
        if output.error_code:
            issues.append(
                {
                    "code": output.error_code,
                    "severity": "warning",
                    "message": output.correction_summary or "请检查第一处错误。",
                    "error_step": output.first_wrong_step,
                }
            )
        topic_keys = [f"{output.chapter}/{topic}" for topic in output.topics]
        await service.students.record_attempt(
            student_id,
            topic_keys or [f"{output.chapter}/general"],
            output.score / 100,
            issues,
        )
    return DirectChatAnswerResponse(
        problem_id=stored.id,
        source_type=source_type,
        sources=sources or [],
        **output.model_dump(),
    )


async def _direct_answer_stream(
    *,
    service: Services,
    student_id: str,
    source_question: str,
    question: str,
    mode: Literal["solve", "review_student_work", "practice"],
    answer_style: Literal["detailed", "concise", "hint"],
    history: list[dict[str, str]],
    reference_question: str | None,
    learner_context: str | None,
    asset_key: str | None = None,
    source_type: Literal["text", "uploaded_image", "ai_generated"] = "text",
    image_bytes: bytes | None = None,
    image_mime: str | None = None,
    chapter: str | None = None,
    topics: list[str] | None = None,
    target_school: str | None = None,
    knowledge_entries: list[KnowledgeEntry] | None = None,
) -> AsyncIterator[bytes]:
    entries = knowledge_entries or []
    async for event, payload in service.direct_tutor.stream_answer(
        question,
        mode=mode,
        answer_style=answer_style,
        history=history,
        reference_question=reference_question,
        learner_context=learner_context,
        image_bytes=image_bytes,
        image_mime=image_mime,
        chapter=chapter,
        topics=topics,
        target_school=target_school,
        knowledge_context=_knowledge_payload(entries),
    ):
        if event == "delta":
            yield _stream_event("delta", text=payload)
            continue
        if not isinstance(payload, DirectTutorOutput):
            continue
        finalized_source = (
            payload.answer_markdown if source_type == "ai_generated" else source_question
        )
        response = await _finalize_direct_answer(
            output=payload,
            service=service,
            student_id=student_id,
            source_question=finalized_source,
            asset_key=asset_key,
            source_type=source_type,
            sources=service.knowledge.citations(entries),
        )
        yield _stream_event("done", response=response.model_dump(mode="json"))


@router.post("/chat/answer", response_model=DirectChatAnswerResponse)
async def direct_chat_answer(
    request: DirectChatAnswerRequest,
    user: CurrentUser,
    service: Services = Depends(get_services),
) -> DirectChatAnswerResponse:
    entries = await _retrieve_knowledge(
        service,
        request.reference_question or request.content,
        target_school=request.target_school,
    )
    output = await service.direct_tutor.answer(
        request.content,
        mode=request.mode,
        answer_style=request.answer_style,
        history=[item.model_dump() for item in request.history],
        reference_question=request.reference_question,
        learner_context=await _learner_context(user.id, service),
        target_school=request.target_school,
        knowledge_context=_knowledge_payload(entries),
    )
    return await _finalize_direct_answer(
        output=output,
        service=service,
        student_id=user.id,
        source_question=request.reference_question or request.content,
        sources=service.knowledge.citations(entries),
    )


@router.post("/chat/answer/stream")
async def direct_chat_answer_stream(
    request: DirectChatAnswerRequest,
    user: CurrentUser,
    service: Services = Depends(get_services),
) -> StreamingResponse:
    entries = await _retrieve_knowledge(
        service,
        request.reference_question or request.content,
        target_school=request.target_school,
    )
    stream = _direct_answer_stream(
        service=service,
        student_id=user.id,
        source_question=request.reference_question or request.content,
        question=request.content,
        mode=request.mode,
        answer_style=request.answer_style,
        history=[item.model_dump() for item in request.history],
        reference_question=request.reference_question,
        learner_context=await _learner_context(user.id, service),
        target_school=request.target_school,
        knowledge_entries=entries,
    )
    return StreamingResponse(
        stream,
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat/answer-image", response_model=DirectChatAnswerResponse)
async def direct_image_answer(
    user: CurrentUser,
    file: UploadFile = File(...),
    content: str = Form(default=""),
    mode: Literal["solve", "review_student_work"] = Form(default="solve"),
    answer_style: Literal["detailed", "concise", "hint"] = Form(default="detailed"),
    history_json: str = Form(default="[]"),
    reference_question: str | None = Form(default=None),
    target_school: str | None = Form(default=None),
    service: Services = Depends(get_services),
) -> DirectChatAnswerResponse:
    raw = await file.read(service.settings.max_image_bytes + 1)
    try:
        asset = await service.storage.save_image(raw, file.content_type)
    except ImageValidationError as exc:
        raise HTTPException(
            status_code=415,
            detail={"code": "invalid_image", "message": str(exc)},
        ) from exc
    normalized = await service.storage.read(asset.key)
    entries = await _retrieve_knowledge(
        service,
        reference_question or content,
        target_school=target_school,
    )
    output = await service.direct_tutor.answer(
        content,
        mode=mode,
        answer_style=answer_style,
        history=_parse_history(history_json),
        reference_question=reference_question,
        learner_context=await _learner_context(user.id, service),
        target_school=target_school,
        knowledge_context=_knowledge_payload(entries),
        image_bytes=normalized,
        image_mime=asset.mime_type,
    )
    return await _finalize_direct_answer(
        output=output,
        service=service,
        student_id=user.id,
        source_question=reference_question or content or "图片题目",
        asset_key=asset.key,
        source_type="uploaded_image",
        sources=service.knowledge.citations(entries),
    )


@router.post("/chat/answer-image/stream")
async def direct_image_answer_stream(
    user: CurrentUser,
    file: UploadFile = File(...),
    content: str = Form(default=""),
    mode: Literal["solve", "review_student_work"] = Form(default="solve"),
    answer_style: Literal["detailed", "concise", "hint"] = Form(default="detailed"),
    history_json: str = Form(default="[]"),
    reference_question: str | None = Form(default=None),
    target_school: str | None = Form(default=None),
    service: Services = Depends(get_services),
) -> StreamingResponse:
    raw = await file.read(service.settings.max_image_bytes + 1)
    try:
        asset = await service.storage.save_image(raw, file.content_type)
    except ImageValidationError as exc:
        raise HTTPException(
            status_code=415,
            detail={"code": "invalid_image", "message": str(exc)},
        ) from exc
    normalized = await service.storage.read(asset.key)
    entries = await _retrieve_knowledge(
        service,
        reference_question or content,
        target_school=target_school,
    )
    stream = _direct_answer_stream(
        service=service,
        student_id=user.id,
        source_question=reference_question or content or "图片题目",
        question=content,
        mode=mode,
        answer_style=answer_style,
        history=_parse_history(history_json),
        reference_question=reference_question,
        learner_context=await _learner_context(user.id, service),
        target_school=target_school,
        knowledge_entries=entries,
        asset_key=asset.key,
        source_type="uploaded_image",
        image_bytes=normalized,
        image_mime=asset.mime_type,
    )
    return StreamingResponse(
        stream,
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/practice/generate", response_model=DirectChatAnswerResponse)
async def generate_practice(
    request: PracticeGenerateRequest,
    user: CurrentUser,
    service: Services = Depends(get_services),
) -> DirectChatAnswerResponse:
    entries = await _retrieve_knowledge(
        service,
        request.source_question,
        target_school=request.target_school,
        chapter=request.chapter,
        topics=request.topics,
    )
    output = await service.direct_tutor.answer(
        request.source_question,
        mode="practice",
        reference_question=request.source_question,
        learner_context=await _learner_context(user.id, service),
        chapter=request.chapter,
        topics=request.topics,
        target_school=request.target_school,
        knowledge_context=_knowledge_payload(entries),
    )
    return await _finalize_direct_answer(
        output=output,
        service=service,
        student_id=user.id,
        source_question=output.answer_markdown,
        source_type="ai_generated",
        sources=service.knowledge.citations(entries),
    )


@router.post("/practice/generate/stream")
async def generate_practice_stream(
    request: PracticeGenerateRequest,
    user: CurrentUser,
    service: Services = Depends(get_services),
) -> StreamingResponse:
    entries = await _retrieve_knowledge(
        service,
        request.source_question,
        target_school=request.target_school,
        chapter=request.chapter,
        topics=request.topics,
    )
    stream = _direct_answer_stream(
        service=service,
        student_id=user.id,
        source_question=request.source_question,
        question=request.source_question,
        mode="practice",
        answer_style="detailed",
        history=[],
        reference_question=request.source_question,
        learner_context=await _learner_context(user.id, service),
        source_type="ai_generated",
        chapter=request.chapter,
        topics=request.topics,
        target_school=request.target_school,
        knowledge_entries=entries,
    )
    return StreamingResponse(
        stream,
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat", response_model=SolveProblemResponse)
async def chat(
    request: DirectSolveRequest,
    user: CurrentUser,
    service: Services = Depends(get_services),
) -> SolveProblemResponse:
    problem = parse_text_problem(request.content, request.student_work)
    stored = await service.problems.create(
        problem, student_id=user.id, conversation_id=request.conversation_id
    )
    solve_request = SolveProblemRequest(
        mode=request.mode,
        student_id=user.id,
        conversation_id=request.conversation_id,
    )
    return await solve_problem(solve_request, service.workflow(stored.id, problem))
