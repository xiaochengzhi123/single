from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
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
from signaltutor.storage.local import ImageValidationError
from signaltutor.workflows.solve_problem import solve_problem

router = APIRouter(prefix="/api/v1", tags=["chat"])
history_adapter = TypeAdapter(list[DirectChatHistoryMessage])


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


async def _finalize_direct_answer(
    *,
    output: DirectTutorOutput,
    service: Services,
    student_id: str,
    source_question: str,
    asset_key: str | None = None,
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
        **output.model_dump(),
    )


@router.post("/chat/answer", response_model=DirectChatAnswerResponse)
async def direct_chat_answer(
    request: DirectChatAnswerRequest,
    user: CurrentUser,
    service: Services = Depends(get_services),
) -> DirectChatAnswerResponse:
    output = await service.direct_tutor.answer(
        request.content,
        mode=request.mode,
        answer_style=request.answer_style,
        history=[item.model_dump() for item in request.history],
        reference_question=request.reference_question,
        learner_context=await _learner_context(user.id, service),
    )
    return await _finalize_direct_answer(
        output=output,
        service=service,
        student_id=user.id,
        source_question=request.reference_question or request.content,
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
    output = await service.direct_tutor.answer(
        content,
        mode=mode,
        answer_style=answer_style,
        history=_parse_history(history_json),
        reference_question=reference_question,
        learner_context=await _learner_context(user.id, service),
        image_bytes=normalized,
        image_mime=asset.mime_type,
    )
    return await _finalize_direct_answer(
        output=output,
        service=service,
        student_id=user.id,
        source_question=reference_question or content or "图片题目",
        asset_key=asset.key,
    )


@router.post("/practice/generate", response_model=DirectChatAnswerResponse)
async def generate_practice(
    request: PracticeGenerateRequest,
    user: CurrentUser,
    service: Services = Depends(get_services),
) -> DirectChatAnswerResponse:
    output = await service.direct_tutor.answer(
        request.source_question,
        mode="practice",
        reference_question=request.source_question,
        learner_context=await _learner_context(user.id, service),
        chapter=request.chapter,
        topics=request.topics,
    )
    return await _finalize_direct_answer(
        output=output,
        service=service,
        student_id=user.id,
        source_question=output.answer_markdown,
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
