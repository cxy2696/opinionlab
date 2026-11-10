"""Authentication, RBAC and tenant-isolation dependencies."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionFactory
from app.errors import ApiError
from app.models import AuditLog, IdempotencyKey, Membership, User
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)
ALL_ROLES = frozenset(
    {"platform_admin", "org_admin", "scenario_owner", "researcher", "analyst", "reviewer"}
)


@dataclass(frozen=True)
class Principal:
    user_id: uuid.UUID
    org_id: uuid.UUID
    role: str
    email: str


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session


async def get_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> Principal:
    if credentials is None:
        raise ApiError(401, "UNAUTHORIZED", "missing bearer token")
    try:
        payload = decode_token(credentials.credentials, "access")
        user_id = uuid.UUID(str(payload["sub"]))
        org_id = uuid.UUID(str(payload["org_id"]))
    except (ValueError, KeyError) as exc:
        raise ApiError(401, "UNAUTHORIZED", "invalid access token") from exc
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise ApiError(401, "UNAUTHORIZED", "user disabled")
    membership = await session.scalar(
        select(Membership).where(
            Membership.user_id == user_id, Membership.org_id == org_id
        )
    )
    if membership is None:
        raise ApiError(403, "FORBIDDEN", "no membership in this org")
    return Principal(user_id=user_id, org_id=org_id, role=membership.role, email=user.email)


def require_roles(*roles: str) -> Callable[..., Any]:
    async def dependency(principal: Principal = Depends(get_principal)) -> Principal:
        if principal.role not in roles:
            raise ApiError(403, "FORBIDDEN", f"role {principal.role} is not allowed")
        return principal

    return dependency


async def write_audit(
    session: AsyncSession,
    principal: Principal,
    action: str,
    target: str,
    detail: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditLog(
            org_id=principal.org_id,
            user_id=principal.user_id,
            action=action,
            target=target,
            detail=detail or {},
        )
    )


async def replay_idempotent(
    session: AsyncSession, principal: Principal, key: str | None, method: str, path: str
) -> tuple[int, dict[str, Any]] | None:
    if not key:
        return None
    row = await session.scalar(
        select(IdempotencyKey).where(
            IdempotencyKey.org_id == principal.org_id,
            IdempotencyKey.key == key,
            IdempotencyKey.method == method,
            IdempotencyKey.path == path,
        )
    )
    if row is None:
        return None
    return row.status_code, dict(row.response)


async def save_idempotent(
    session: AsyncSession,
    principal: Principal,
    key: str | None,
    method: str,
    path: str,
    status_code: int,
    response: dict[str, Any],
) -> None:
    if not key:
        return
    session.add(
        IdempotencyKey(
            org_id=principal.org_id,
            key=key,
            method=method,
            path=path,
            status_code=status_code,
            response=response,
        )
    )
