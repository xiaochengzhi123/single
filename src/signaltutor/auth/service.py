from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from signaltutor.schemas.auth import AdminAccountResponse, AuthUser


class AccountConflictError(ValueError):
    pass


class InvalidCredentialsError(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt$16384$8$1${_b64url(salt)}${_b64url(derived)}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$")
        if algorithm != "scrypt":
            return False
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_b64url_decode(salt),
            n=int(n),
            r=int(r),
            p=int(p),
        )
        return hmac.compare_digest(_b64url(derived), expected)
    except (ValueError, TypeError):
        return False


class AuthService:
    def __init__(self, path: Path, secret: str, token_ttl_seconds: int) -> None:
        self.path = path
        self.secret = secret.encode("utf-8")
        self.token_ttl_seconds = token_ttl_seconds
        self._lock = asyncio.Lock()

    def _read(self) -> dict:
        if not self.path.exists():
            return {"accounts": []}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"accounts": []}
        data.setdefault("accounts", [])
        return data

    def _write(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)
        self.path.chmod(0o600)

    @staticmethod
    def _public_account(row: dict) -> AdminAccountResponse:
        return AdminAccountResponse(
            id=row["id"],
            username=row["username"],
            display_name=row["display_name"],
            active=bool(row["active"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    async def create_account(
        self,
        *,
        username: str,
        display_name: str,
        password: str,
    ) -> AdminAccountResponse:
        normalized = username.lower()
        async with self._lock:
            data = self._read()
            if any(row["username"] == normalized for row in data["accounts"]):
                raise AccountConflictError("该用户名已经存在")
            row = {
                "id": f"usr_{uuid4()}",
                "username": normalized,
                "display_name": display_name.strip(),
                "password_hash": _hash_password(password),
                "active": True,
                "session_version": 1,
                "created_at": _now().isoformat(),
            }
            data["accounts"].append(row)
            self._write(data)
            return self._public_account(row)

    async def list_accounts(self) -> list[AdminAccountResponse]:
        async with self._lock:
            rows = self._read()["accounts"]
            return [self._public_account(row) for row in reversed(rows)]

    async def set_active(self, account_id: str, active: bool) -> AdminAccountResponse | None:
        async with self._lock:
            data = self._read()
            for row in data["accounts"]:
                if row["id"] == account_id:
                    row["active"] = active
                    row["session_version"] = int(row.get("session_version", 1)) + 1
                    self._write(data)
                    return self._public_account(row)
            return None

    async def reset_password(self, account_id: str, password: str) -> AdminAccountResponse | None:
        async with self._lock:
            data = self._read()
            for row in data["accounts"]:
                if row["id"] == account_id:
                    row["password_hash"] = _hash_password(password)
                    row["session_version"] = int(row.get("session_version", 1)) + 1
                    self._write(data)
                    return self._public_account(row)
            return None

    async def authenticate(self, username: str, password: str) -> tuple[str, AuthUser]:
        normalized = username.lower()
        async with self._lock:
            row = next(
                (item for item in self._read()["accounts"] if item["username"] == normalized),
                None,
            )
        if not row or not row["active"] or not _verify_password(password, row["password_hash"]):
            raise InvalidCredentialsError("账号或密码错误")
        user = AuthUser(
            id=row["id"],
            username=row["username"],
            display_name=row["display_name"],
        )
        return self._issue_token(row), user

    def _issue_token(self, row: dict) -> str:
        expires_at = _now() + timedelta(seconds=self.token_ttl_seconds)
        payload = {
            "sub": row["id"],
            "usr": row["username"],
            "ver": int(row.get("session_version", 1)),
            "exp": int(expires_at.timestamp()),
        }
        encoded = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signature = _b64url(hmac.new(self.secret, encoded.encode("ascii"), hashlib.sha256).digest())
        return f"{encoded}.{signature}"

    async def verify_token(self, token: str) -> AuthUser:
        try:
            encoded, signature = token.split(".", 1)
            expected = _b64url(
                hmac.new(self.secret, encoded.encode("ascii"), hashlib.sha256).digest()
            )
            if not hmac.compare_digest(signature, expected):
                raise InvalidCredentialsError("登录已失效")
            payload = json.loads(_b64url_decode(encoded))
            if int(payload["exp"]) <= int(_now().timestamp()):
                raise InvalidCredentialsError("登录已过期")
        except (ValueError, KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise InvalidCredentialsError("登录已失效") from exc

        async with self._lock:
            row = next(
                (item for item in self._read()["accounts"] if item["id"] == payload["sub"]),
                None,
            )
        if (
            not row
            or not row["active"]
            or int(row.get("session_version", 1)) != int(payload["ver"])
        ):
            raise InvalidCredentialsError("登录已失效")
        return AuthUser(
            id=row["id"],
            username=row["username"],
            display_name=row["display_name"],
        )
