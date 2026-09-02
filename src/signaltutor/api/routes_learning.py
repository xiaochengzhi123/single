from fastapi import APIRouter, Depends, HTTPException

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
    return await service.students.save_mistake(
        **(request.model_dump() | {"student_id": user.id})
    )


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
    return row
