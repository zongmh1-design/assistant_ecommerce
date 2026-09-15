"""End-to-end HTTP tests for login and current-user authentication."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import decode_access_token, hash_password
from app.models.user import User, UserRole, UserStatus


PASSWORD = "CorrectPassword123!"


def create_user(
    db: Session,
    *,
    username: str = "alice",
    role: UserRole = UserRole.OPERATOR,
    status: UserStatus = UserStatus.ACTIVE,
) -> User:
    user = User(
        username=username,
        display_name=username.title(),
        password_hash=hash_password(PASSWORD),
        role=role,
        status=status,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login(client: TestClient, username: str, password: str = PASSWORD) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_correct_username_and_password_login_success(
    client: TestClient, db_session: Session
) -> None:
    user = create_user(db_session)
    response = client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": PASSWORD},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    token_payload = decode_access_token(response.json()["access_token"])
    assert token_payload["user_id"] == user.id
    assert token_payload["role"] == "operator"
    assert "exp" in token_payload
    db_session.refresh(user)
    assert user.last_login_at is not None


def test_wrong_password_login_fails(client: TestClient, db_session: Session) -> None:
    create_user(db_session)
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "WrongPassword123!"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_disabled_user_cannot_login(client: TestClient, db_session: Session) -> None:
    create_user(db_session, status=UserStatus.DISABLED)
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": PASSWORD},
    )

    assert response.status_code == 401


def test_auth_me_succeeds_with_valid_token(
    client: TestClient, db_session: Session
) -> None:
    user = create_user(db_session, role=UserRole.ADMIN)
    token = login(client, user.username)
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == user.id
    assert response.json()["role"] == "admin"
    assert "password_hash" not in response.json()


def test_auth_me_rejects_missing_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


def test_auth_me_rejects_invalid_token(client: TestClient) -> None:
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer definitely-not-a-jwt"},
    )
    assert response.status_code == 401


def test_existing_token_is_rejected_after_user_is_disabled(
    client: TestClient, db_session: Session
) -> None:
    user = create_user(db_session)
    token = login(client, user.username)
    user.status = UserStatus.DISABLED
    db_session.commit()

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
