from fastapi import APIRouter, Depends

from signaltutor.api.auth_dependencies import CurrentUser
from signaltutor.api.dependencies import Services, get_services
from signaltutor.schemas.api import FeedbackRequest

router = APIRouter(prefix="/api/v1", tags=["feedback"])


@router.post("/feedback", status_code=201)
async def feedback(
    request: FeedbackRequest,
    user: CurrentUser,
    service: Services = Depends(get_services),
) -> dict:
    await service.problems.add_feedback(request.model_dump() | {"student_id": user.id})
    return {"status": "recorded"}
