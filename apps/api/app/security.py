"""Password hashing (argon2id) and JWT issuance/verification."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jwt import InvalidTokenError

from app.settings import settings

# argon2id with m=64MB, t=3, p=4
PASSWORD_HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
ACCESS_MINUTES = 30
REFRESH_DAYS = 14


def hash_password(password: str) -> str:
    return PASSWORD_HASHER.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return PASSWORD_HASHER.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def _token(
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    role: str,
    token_type: str,
    expires: timedelta,
    jti: uuid.UUID | None = None,
) -> tuple[str, uuid.UUID, datetime]:
    identifier = jti or uuid.uuid4()
    expires_at = datetime.now(UTC) + expires
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "org_id": str(org_id),
        "role": role,
        "type": token_type,
        "jti": str(identifier),
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256"), identifier, expires_at


def create_access_token(user_id: uuid.UUID, org_id: uuid.UUID, role: str) -> str:
    token, _, _ = _token(user_id, org_id, role, "access", timedelta(minutes=ACCESS_MINUTES))
    return token


def create_refresh_token(
    user_id: uuid.UUID, org_id: uuid.UUID, role: str
) -> tuple[str, uuid.UUID, datetime]:
    return _token(user_id, org_id, role, "refresh", timedelta(days=REFRESH_DAYS))


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except InvalidTokenError as exc:
        raise ValueError("invalid token") from exc
    if payload.get("type") != expected_type:
        raise ValueError("wrong token type")
    return dict(payload)
