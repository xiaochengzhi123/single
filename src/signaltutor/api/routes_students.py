from fastapi import APIRouter, Depends

from signaltutor.api.auth_dependencies import CurrentUser
from signaltutor.api.dependencies import Services, get_services

router = APIRouter(prefix="/api/v1/students", tags=["students"])


@router.get("/me/mastery")
async def mastery(
    user: CurrentUser,
    service: Services = Depends(get_services),
) -> dict:
    rows = await service.students.get_mastery(user.id)
    return {"student_id": user.id, "topics": [row.model_dump(mode="json") for row in rows]}


@router.get("/me/errors")
async def errors(
    user: CurrentUser,
    service: Services = Depends(get_services),
) -> dict:
    return {"student_id": user.id, "errors": await service.students.get_errors(user.id)}


@router.get("/me/overview")
async def overview(
    user: CurrentUser,
    service: Services = Depends(get_services),
) -> dict:
    return await service.students.get_overview(user.id)
