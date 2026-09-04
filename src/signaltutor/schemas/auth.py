from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

USERNAME_PATTERN = r"^[A-Za-z0-9_.-]+$"


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=USERNAME_PATTERN)
    password: str = Field(min_length=8, max_length=128)


class AuthUser(BaseModel):
    id: str
    username: str
    display_name: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUser


class AdminAccountCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=USERNAME_PATTERN)
    display_name: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    subscription_months: int = Field(default=1, ge=1, le=36)


class AdminAccountUpdateRequest(BaseModel):
    active: bool


class AdminPasswordResetRequest(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class AdminSubscriptionRenewRequest(BaseModel):
    months: int = Field(ge=1, le=36)


class AdminAccountResponse(AuthUser):
    active: bool
    created_at: datetime
    expires_at: datetime
    expired: bool
    remaining_days: int
