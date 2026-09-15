"""Authentication use case: verify credentials and record successful login."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.security import create_access_token, verify_password
from app.models.user import UserStatus
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def login(self, *, username: str, password: str) -> str:
        user = self.users.get_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            raise _invalid_credentials_error()
        if user.status is not UserStatus.ACTIVE:
            # 对外仍返回同一错误，避免泄露账号是否存在或是否被禁用。
            raise _invalid_credentials_error()

        self.users.record_login(user, datetime.now(timezone.utc))
        self.db.commit()
        return create_access_token(user_id=user.id, role=user.role)


def _invalid_credentials_error() -> AppError:
    return AppError(
        status_code=401,
        code="invalid_credentials",
        message="Invalid username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )
