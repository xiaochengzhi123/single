from fastapi import APIRouter, Depends, HTTPException

from signaltutor.api.auth_dependencies import AdminAccess, CurrentUser
from signaltutor.api.dependencies import Services, get_services
from signaltutor.auth import AccountConflictError, InvalidCredentialsError
from signaltutor.schemas.auth import (
    AdminAccountCreateRequest,
    AdminAccountResponse,
    AdminAccountUpdateRequest,
    AdminPasswordResetRequest,
    AdminSubscriptionRenewRequest,
    AuthUser,
    LoginRequest,
    LoginResponse,
)

router = APIRouter(prefix="/api/v1", tags=["auth"])


@router.post("/auth/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    service: Services = Depends(get_services),
) -> LoginResponse:
    try:
        token, user = await service.auth.authenticate(request.username, request.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail={"message": str(exc)}) from exc
    return LoginResponse(
        access_token=token,
        expires_in=service.settings.access_token_ttl_seconds,
        user=user,
    )


@router.get("/auth/me", response_model=AuthUser)
async def me(user: CurrentUser) -> AuthUser:
    return user


@router.get("/admin/accounts", response_model=list[AdminAccountResponse])
async def list_accounts(
    _admin: AdminAccess,
    service: Services = Depends(get_services),
) -> list[AdminAccountResponse]:
    return await service.auth.list_accounts()


@router.post("/admin/accounts", response_model=AdminAccountResponse, status_code=201)
async def create_account(
    request: AdminAccountCreateRequest,
    _admin: AdminAccess,
    service: Services = Depends(get_services),
) -> AdminAccountResponse:
    try:
        return await service.auth.create_account(**request.model_dump())
    except AccountConflictError as exc:
        raise HTTPException(status_code=409, detail={"message": str(exc)}) from exc


@router.patch("/admin/accounts/{account_id}", response_model=AdminAccountResponse)
async def update_account(
    account_id: str,
    request: AdminAccountUpdateRequest,
    _admin: AdminAccess,
    service: Services = Depends(get_services),
) -> AdminAccountResponse:
    account = await service.auth.set_active(account_id, request.active)
    if not account:
        raise HTTPException(status_code=404, detail={"message": "账号不存在"})
    return account


@router.post("/admin/accounts/{account_id}/reset-password", response_model=AdminAccountResponse)
async def reset_password(
    account_id: str,
    request: AdminPasswordResetRequest,
    _admin: AdminAccess,
    service: Services = Depends(get_services),
) -> AdminAccountResponse:
    account = await service.auth.reset_password(account_id, request.password)
    if not account:
        raise HTTPException(status_code=404, detail={"message": "账号不存在"})
    return account


@router.post("/admin/accounts/{account_id}/renew", response_model=AdminAccountResponse)
async def renew_subscription(
    account_id: str,
    request: AdminSubscriptionRenewRequest,
    _admin: AdminAccess,
    service: Services = Depends(get_services),
) -> AdminAccountResponse:
    account = await service.auth.renew_subscription(account_id, request.months)
    if not account:
        raise HTTPException(status_code=404, detail={"message": "账号不存在"})
    return account
