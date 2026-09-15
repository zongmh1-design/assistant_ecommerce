"""Interactively create the first administrator after Alembic migration."""

import argparse
import getpass

from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole, UserStatus
from app.repositories.user_repository import UserRepository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an administrator account")
    parser.add_argument("--username", required=True)
    parser.add_argument("--display-name", required=True)
    return parser.parse_args()


def read_password() -> str:
    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise ValueError("Passwords do not match")
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters")
    return password


def main() -> int:
    args = parse_args()
    username = args.username.strip()
    display_name = args.display_name.strip()
    if not username or not display_name:
        print("Username and display name cannot be blank")
        return 1

    try:
        plain_password = read_password()
    except ValueError as exc:
        print(str(exc))
        return 1

    with SessionLocal() as db:
        repository = UserRepository(db)
        if repository.get_by_username(username) is not None:
            print(f"User '{username}' already exists")
            return 1

        repository.add(
            User(
                username=username,
                display_name=display_name,
                password_hash=hash_password(plain_password),
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE,
            )
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            print("Administrator could not be created because the username exists")
            return 1

    print(f"Administrator '{username}' created")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
