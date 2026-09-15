"""HTTP-level checks for reusable admin/operator/viewer dependencies."""

from collections.abc import Generator
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_admin, require_write_access
from app.core.database import get_db
from app.core.exceptions import register_exception_handlers
from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole, UserStatus


permission_app = FastAPI()
register_exception_handlers(permission_app)


@permission_app.post("/test/admin-only")
def admin_only(_: Annotated[User, Depends(require_admin)]) -> dict[str, bool]:
    return {"allowed": True}


@permission_app.post("/test/write")
def write_access(
    _: Annotated[User, Depends(require_write_access)],
) -> dict[str, bool]:
    return {"allowed": True}


@pytest.fixture
def permission_client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    permission_app.dependency_overrides[get_db] = override_get_db
    with TestClient(permission_app) as test_client:
        yield test_client
    permission_app.dependency_overrides.clear()


def create_role_token(db: Session, role: UserRole) -> str:
    user = User(
        username=f"{role.value}_user",
        display_name=role.value.title(),
        password_hash=hash_password("PermissionPassword123!"),
        role=role,
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return create_access_token(user_id=user.id, role=user.role)


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_admin_permission_passes(
    permission_client: TestClient, db_session: Session
) -> None:
    token = create_role_token(db_session, UserRole.ADMIN)
    response = permission_client.post(
        "/test/admin-only", headers=auth_header(token)
    )
    assert response.status_code == 200


def test_operator_write_permission_passes(
    permission_client: TestClient, db_session: Session
) -> None:
    token = create_role_token(db_session, UserRole.OPERATOR)
    response = permission_client.post("/test/write", headers=auth_header(token))
    assert response.status_code == 200


def test_operator_admin_permission_is_rejected(
    permission_client: TestClient, db_session: Session
) -> None:
    token = create_role_token(db_session, UserRole.OPERATOR)
    response = permission_client.post(
        "/test/admin-only", headers=auth_header(token)
    )
    assert response.status_code == 403


def test_viewer_write_permission_is_rejected(
    permission_client: TestClient, db_session: Session
) -> None:
    token = create_role_token(db_session, UserRole.VIEWER)
    response = permission_client.post("/test/write", headers=auth_header(token))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"
