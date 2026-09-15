"""Reusable authentication and role-based authorization dependencies."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.security import TokenDecodeError, decode_access_token
from app.models.user import User, UserRole, UserStatus
from app.repositories.user_repository import UserRepository


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_active_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _authentication_error()
    try:
        payload = decode_access_token(credentials.credentials)
    except TokenDecodeError as exc:
        raise _authentication_error() from exc

    user = UserRepository(db).get_by_id(payload["user_id"])
    if user is None or user.status is not UserStatus.ACTIVE:
        raise _authentication_error()
    if user.role.value != payload["role"]:
        # 角色变更后旧 Token 立即失效，必须重新登录取得新权限。
        raise _authentication_error()
    return user


CurrentUser = Annotated[User, Depends(get_current_active_user)]


def require_roles(*allowed_roles: UserRole) -> Callable[[CurrentUser], User]:
    allowed = frozenset(allowed_roles)

    def role_dependency(current_user: CurrentUser) -> User:
        if current_user.role not in allowed:
            raise AppError(
                status_code=403,
                code="permission_denied",
                message="You do not have permission to perform this action",
            )
        return current_user

    return role_dependency


require_admin = require_roles(UserRole.ADMIN)
require_write_access = require_roles(UserRole.ADMIN, UserRole.OPERATOR)


def _authentication_error() -> AppError:
    return AppError(
        status_code=401,
        code="invalid_token",
        message="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
