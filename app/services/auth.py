from typing import Optional

import hashlib
import hmac
import os
from app.db.database import execute, fetch_one
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


def _generated_email(name: str) -> str:
    slug = "".join(ch.lower() for ch in name if ch.isalnum()) or "user"
    random_suffix = os.urandom(4).hex()
    return f"{slug}.{random_suffix}@local.uns"


def create_user(name: str, password: str) -> UserProfile:
    existing = fetch_one(
        "SELECT id FROM users WHERE name = ?",
        (name,),
    )
    if existing is not None:
        raise ValueError("Name already exists")

    password_hash = _hash_password(password, os.urandom(16))
    generated_email = _generated_email(name)
    execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, generated_email, password_hash),
    )
    row = fetch_one(
        "SELECT id, name FROM users WHERE name = ?",
        (name,),
    )

    return UserProfile(id=row["id"], name=row["name"])


def get_user_by_id(user_id: int) -> Optional[dict]:
    row = fetch_one(
        "SELECT id, name FROM users WHERE id = ?",
        (user_id,),
    )
    if row is None:
        return None
    return {"id": row["id"], "name": row["name"], "email": None}


def authenticate_user(name: str, password: str) -> Optional[UserProfile]:
    row = fetch_one(
        "SELECT id, name, password_hash FROM users WHERE name = ?",
        (name,),
    )

    if row is None:
        return None
    if not _verify_password(password, row["password_hash"]):
        return None

    return UserProfile(id=row["id"], name=row["name"])
