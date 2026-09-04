from datetime import UTC, datetime

import pytest

import signaltutor.auth.service as auth_module
from signaltutor.auth.service import AuthService, InvalidCredentialsError


async def test_subscription_uses_calendar_months_and_blocks_expired_account(
    tmp_path,
    monkeypatch,
) -> None:
    clock = {"now": datetime(2026, 1, 31, 10, tzinfo=UTC)}
    monkeypatch.setattr(auth_module, "_now", lambda: clock["now"])
    service = AuthService(tmp_path / "accounts.json", "test-secret", 60 * 24 * 60 * 60)

    account = await service.create_account(
        username="calendar-student",
        display_name="日历月测试",
        password="Password-2026",
        subscription_months=1,
    )
    token, _ = await service.authenticate("calendar-student", "Password-2026")

    assert account.expires_at == datetime(2026, 2, 28, 10, tzinfo=UTC)

    clock["now"] = datetime(2026, 3, 1, 10, tzinfo=UTC)
    with pytest.raises(InvalidCredentialsError, match="账号已到期"):
        await service.authenticate("calendar-student", "Password-2026")
    with pytest.raises(InvalidCredentialsError, match="账号已到期"):
        await service.verify_token(token)

    renewed = await service.renew_subscription(account.id, 1)

    assert renewed is not None
    assert renewed.expires_at == datetime(2026, 4, 1, 10, tzinfo=UTC)
    assert renewed.expired is False
    await service.authenticate("calendar-student", "Password-2026")
