"""Password hashing and JWT access-token helpers."""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.models.user import UserRole


password_hash = PasswordHash.recommended()


class TokenDecodeError(ValueError):
    """Raised when an access token is invalid or missing required claims."""


def hash_password(plain_password: str) -> str:
    return password_hash.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return password_hash.verify(plain_password, hashed_password)
    except Exception:
        # 损坏或非本系统生成的哈希视为验证失败，禁止让底层异常泄露到接口。
        return False


def create_access_token(*, user_id: int, role: UserRole) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "user_id": user_id,
        "role": role.value,
        "exp": expires_at,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["user_id", "role", "exp"]},
        )
    except InvalidTokenError as exc:
        raise TokenDecodeError("Invalid access token") from exc

    user_id = payload.get("user_id")
    role = payload.get("role")
    if not isinstance(user_id, int) or user_id <= 0:
        raise TokenDecodeError("Invalid user_id claim")
    if role not in {item.value for item in UserRole}:
        raise TokenDecodeError("Invalid role claim")
    return payload
