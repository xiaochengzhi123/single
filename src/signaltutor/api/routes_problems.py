from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from signaltutor.agents.text_parser import parse_text_problem
from signaltutor.api.auth_dependencies import CurrentUser
from signaltutor.api.dependencies import Services, get_services
from signaltutor.schemas.api import ParseResponse, SolveProblemRequest, SolveProblemResponse
from signaltutor.schemas.problem import ProblemParse, TextParseRequest, UncertainElement
from signaltutor.storage.local import ImageValidationError
from signaltutor.workflows.solve_problem import solve_problem

router = APIRouter(prefix="/api/v1/problems", tags=["problems"])


@router.post("/parse-text", response_model=ParseResponse)
async def parse_text(
    request: TextParseRequest,
    user: CurrentUser,
    service: Services = Depends(get_services),
) -> ParseResponse:
    problem = parse_text_problem(request.content, request.student_work)
    stored = await service.problems.create(
        problem, student_id=user.id, conversation_id=request.conversation_id
    )
    return ParseResponse(status="ok", problem_id=stored.id, problem_parse=problem)


@router.post("/upload", response_model=ParseResponse)
async def upload_problem(
    user: CurrentUser,
    file: UploadFile = File(...),
    conversation_id: str | None = Form(default=None),
    service: Services = Depends(get_services),
) -> ParseResponse:
    raw = await file.read(service.settings.max_image_bytes + 1)
    try:
        asset = await service.storage.save_image(raw, file.content_type)
    except ImageValidationError as exc:
        raise HTTPException(
            status_code=415, detail={"code": "invalid_image", "message": str(exc)}
        ) from exc
    normalized = await service.storage.read(asset.key)
    if service.vision:
        problem = await service.vision.parse(normalized, asset.mime_type)
    else:
        problem = ProblemParse(
            input_type="image",
            question_text="",
            known_conditions=[],
            target="请确认图片识别内容",
            formulas=[],
            figures=[],
            uncertain_elements=[
                UncertainElement(
                    description="未配置 DASHSCOPE_API_KEY，无法执行视觉结构化解析",
                    location="整张图片",
                    candidates=[],
                    confidence=0,
                )
            ],
            signal_domain="unknown",
            confidence=0,
        )
    stored = await service.problems.create(
        problem,
        student_id=user.id,
        conversation_id=conversation_id,
        asset_key=asset.key,
    )
    status = (
        "needs_confirmation"
        if problem.confidence < service.settings.vision_confidence_threshold
        or problem.uncertain_elements
        else "ok"
    )
    return ParseResponse(status=status, problem_id=stored.id, problem_parse=problem)


@router.post("/{problem_id}/solve", response_model=SolveProblemResponse)
async def solve_saved_problem(
    problem_id: str,
    request: SolveProblemRequest,
    user: CurrentUser,
    service: Services = Depends(get_services),
) -> SolveProblemResponse:
    stored = await service.problems.get(problem_id)
    if not stored or stored.student_id != user.id:
        raise HTTPException(status_code=404, detail={"code": "problem_not_found"})
    if request.confirmed_problem:
        await service.problems.update_parse(problem_id, request.confirmed_problem)
    authenticated_request = request.model_copy(update={"student_id": user.id})
    return await solve_problem(authenticated_request, service.workflow(problem_id, stored.parse))


@router.post("/{problem_id}/solve/stream")
async def solve_saved_problem_stream(
    problem_id: str,
    request: SolveProblemRequest,
    user: CurrentUser,
    service: Services = Depends(get_services),
) -> StreamingResponse:
    stored = await service.problems.get(problem_id)
    if not stored or stored.student_id != user.id:
        raise HTTPException(status_code=404, detail={"code": "problem_not_found"})
    authenticated_request = request.model_copy(update={"student_id": user.id})
    result = await solve_problem(
        authenticated_request,
        service.workflow(problem_id, stored.parse),
    )

    async def events() -> AsyncIterator[str]:
        for event in result.workflow_events:
            yield f"event: {event}\ndata: {{}}\n\n"
        if result.answer:
            yield (
                "event: answer_delta\ndata: "
                + json.dumps({"delta": result.answer}, ensure_ascii=False)
                + "\n\n"
            )
        yield "event: done\ndata: " + result.model_dump_json() + "\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
