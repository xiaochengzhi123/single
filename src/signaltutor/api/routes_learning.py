import mimetypes

from fastapi import APIRouter, Depends, HTTPException, Response

from signaltutor.api.auth_dependencies import CurrentUser
from signaltutor.api.dependencies import Services, get_services
from signaltutor.schemas.api import MistakeCreateRequest, MistakeUpdateRequest

router = APIRouter(prefix="/api/v1/mistakes", tags=["learning"])


@router.post("", status_code=201)
async def create_mistake(
    request: MistakeCreateRequest,
    user: CurrentUser,
    service: Services = Depends(get_services),
) -> dict:
    image_key = None
    if request.problem_id:
        problem = await service.problems.get(request.problem_id)
        if problem and problem.student_id == user.id:
            image_key = problem.asset_key
    row = await service.students.save_mistake(
        **(request.model_dump() | {"student_id": user.id, "image_key": image_key})
    )
    public_row = row | {"has_image": bool(row.get("image_key"))}
    public_row.pop("image_key", None)
    return public_row


@router.get("")
async def list_mistakes(
    user: CurrentUser,
    service: Services = Depends(get_services),
) -> dict:
    return {
        "student_id": user.id,
        "mistakes": await service.students.list_mistakes(user.id),
    }


@router.patch("/{mistake_id}")
async def update_mistake(
    mistake_id: str,
    request: MistakeUpdateRequest,
    user: CurrentUser,
    service: Services = Depends(get_services),
) -> dict:
    row = await service.students.set_mistake_mastered(
        user.id,
        mistake_id,
        request.mastered,
    )
    if not row:
        raise HTTPException(status_code=404, detail={"message": "未找到这条错题记录"})
    public_row = row | {"has_image": bool(row.get("image_key"))}
    public_row.pop("image_key", None)
    return public_row


@router.get("/{mistake_id}/image")
async def get_mistake_image(
    mistake_id: str,
    user: CurrentUser,
    service: Services = Depends(get_services),
) -> Response:
    row = await service.students.get_mistake(user.id, mistake_id)
    image_key = row.get("image_key") if row else None
    if not image_key:
        raise HTTPException(status_code=404, detail={"message": "这条错题没有保存图片"})
    try:
        content = await service.storage.read(image_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"message": "题目图片不存在"}) from exc
    media_type = mimetypes.guess_type(image_key)[0] or "application/octet-stream"
    return Response(content=content, media_type=media_type)
