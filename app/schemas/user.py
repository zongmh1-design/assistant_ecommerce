"""Public User schema; password_hash is intentionally excluded."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole, UserStatus


class UserRead(BaseModel):
    id: int
    username: str
    display_name: str
    role: UserRole
    status: UserStatus
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
