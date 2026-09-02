from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException

from signaltutor.api.dependencies import Services, get_services
from signaltutor.auth import InvalidCredentialsError
from signaltutor.schemas.auth import AuthUser


async def require_user(
    authorization: Annotated[str | None, Header()] = None,
    service: Services = Depends(get_services),
) -> AuthUser:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail={"message": "请先登录"})
    try:
        return await service.auth.verify_token(token.strip())
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail={"message": str(exc)}) from exc


async def require_admin(
    x_admin_key: Annotated[str | None, Header()] = None,
    service: Services = Depends(get_services),
) -> None:
    if not x_admin_key or not hmac.compare_digest(x_admin_key, service.settings.admin_api_key):
        raise HTTPException(status_code=401, detail={"message": "管理员密钥错误"})


CurrentUser = Annotated[AuthUser, Depends(require_user)]
AdminAccess = Annotated[None, Depends(require_admin)]
