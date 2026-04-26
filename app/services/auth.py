from typing import Optional

import hashlib
import hmac
import os

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.database import get_engine, users_table
from app.schemas.auth import UserProfile


def _hash_password(password: str, salt: bytes) -> str:
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, 100_000
    )
    return f"{salt.hex()}${password_hash.hex()}"


def _verify_password(password: str, encoded_password: str) -> bool:
    salt_hex, password_hash_hex = encoded_password.split("$", maxsplit=1)
    expected = _hash_password(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(expected, f"{salt_hex}${password_hash_hex}")


def create_user(username: str, password: str) -> UserProfile:
    password_hash = _hash_password(password, os.urandom(16))

    try:
        with get_engine().begin() as connection:
            connection.execute(
                users_table.insert().values(
                    username=username,
                    password_hash=password_hash,
                )
            )
    except IntegrityError as exc:
        raise ValueError("Username already exists") from exc

    return UserProfile(username=username)


def get_user_by_username(username: str) -> Optional[UserProfile]:
    statement = select(users_table.c.username).where(users_table.c.username == username)
    with get_engine().connect() as connection:
        row = connection.execute(statement).mappings().first()

    if row is None:
        return None

    return UserProfile(username=row["username"])


def authenticate_user(username: str, password: str) -> Optional[UserProfile]:
    statement = select(
        users_table.c.username,
        users_table.c.password_hash,
    ).where(users_table.c.username == username)
    with get_engine().connect() as connection:
        row = connection.execute(statement).mappings().first()

    if row is None:
        return None
    if not _verify_password(password, row["password_hash"]):
        return None

    return UserProfile(username=row["username"])
