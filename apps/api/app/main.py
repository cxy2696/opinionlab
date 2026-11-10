"""FastAPI application: auth, RBAC, tenant isolation and audit (US-017)."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import (
    Principal,
    get_principal,
    get_session,
    replay_idempotent,
    require_roles,
    save_idempotent,
    write_audit,
)
from app.errors import ApiError, api_error_handler
from app.models import (
    Dataset,
    Membership,
    Org,
    RefreshToken,
    Run,
    RunShare,
    Scenario,
    User,
    utcnow,
)
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from hnle.spec import ModelSpec

app = FastAPI(title="OpinionLab API", version="0.1.0")
app.add_exception_handler(ApiError, api_error_handler)  # type: ignore[arg-type]

api = APIRouter(prefix="/api/v1")
auth = APIRouter(prefix="/api/v1/auth")


@app.middleware("http")
async def trace_middleware(request: Request, call_next: Any) -> Any:
    request.state.trace_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "SPEC_INVALID",
                "message": "request validation failed",
                "details": exc.errors(),
                "trace_id": getattr(request.state, "trace_id", ""),
            }
        },
    )


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ScenarioCreate(BaseModel):
    name: str
    spec: dict[str, Any]
    description: str | None = None
    template_key: str | None = None


class ScenarioPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    spec: dict[str, Any] | None = None


class RunCreate(BaseModel):
    scenario_id: uuid.UUID
    repeats: int | None = Field(default=None, ge=1, le=500)
    seed: int | None = Field(default=None, ge=0)


def _validate_spec(spec: dict[str, Any]) -> str:
    try:
        parsed = ModelSpec.model_validate(spec)
    except Exception as exc:  # noqa: BLE001 - converted to API error below
        errors: list[Any] = getattr(exc, "errors", lambda: [])()
        raise ApiError(
            422, "SPEC_INVALID", "ModelSpec validation failed", {"errors": errors}
        ) from exc
    canonical = parsed.canonical_json()
    return hashlib.sha256(canonical.encode()).hexdigest()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@auth.post("/login", response_model=TokenPair)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)) -> TokenPair:
    user = await session.scalar(select(User).where(User.email == body.email))
    if user is None:
        raise ApiError(401, "INVALID_CREDENTIALS", "email or password is incorrect")
    now = datetime.now(UTC)
    if user.locked_until is not None and user.locked_until > now:
        raise ApiError(423, "LOCKED", "account temporarily locked", {"retry_after": 900})
    if not verify_password(user.password_hash, body.password):
        user.failed_login_count += 1
        if user.failed_login_count >= 5:
            user.locked_until = now.replace(microsecond=0) + __import__("datetime").timedelta(
                minutes=15
            )
            user.failed_login_count = 0
        await session.commit()
        raise ApiError(401, "INVALID_CREDENTIALS", "email or password is incorrect")
    membership = await session.scalar(select(Membership).where(Membership.user_id == user.id))
    if membership is None:
        raise ApiError(403, "FORBIDDEN", "user has no organisation membership")
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    access = create_access_token(user.id, membership.org_id, membership.role)
    refresh, jti, expires_at = create_refresh_token(user.id, membership.org_id, membership.role)
    session.add(
        RefreshToken(jti=jti, user_id=user.id, org_id=membership.org_id, expires_at=expires_at)
    )
    await session.commit()
    return TokenPair(access_token=access, refresh_token=refresh)


@auth.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, session: AsyncSession = Depends(get_session)) -> TokenPair:
    try:
        payload = decode_token(body.refresh_token, "refresh")
        jti = uuid.UUID(str(payload["jti"]))
        user_id = uuid.UUID(str(payload["sub"]))
    except (ValueError, KeyError) as exc:
        raise ApiError(401, "UNAUTHORIZED", "invalid refresh token") from exc
    stored = await session.get(RefreshToken, jti)
    if stored is None or stored.revoked or stored.expires_at <= datetime.now(UTC):
        raise ApiError(401, "UNAUTHORIZED", "refresh token revoked or expired")
    membership = await session.scalar(select(Membership).where(Membership.user_id == user_id))
    if membership is None:
        raise ApiError(403, "FORBIDDEN", "membership missing")
    stored.revoked = True
    access = create_access_token(user_id, membership.org_id, membership.role)
    new_refresh, new_jti, expires_at = create_refresh_token(
        user_id, membership.org_id, membership.role
    )
    session.add(
        RefreshToken(jti=new_jti, user_id=user_id, org_id=membership.org_id, expires_at=expires_at)
    )
    await session.commit()
    return TokenPair(access_token=access, refresh_token=new_refresh)


@auth.post("/logout")
async def logout(
    body: RefreshRequest, session: AsyncSession = Depends(get_session)
) -> dict[str, str]:
    try:
        payload = decode_token(body.refresh_token, "refresh")
        stored = await session.get(RefreshToken, uuid.UUID(str(payload["jti"])))
    except (ValueError, KeyError) as exc:
        raise ApiError(401, "UNAUTHORIZED", "invalid refresh token") from exc
    if stored is not None:
        stored.revoked = True
        await session.commit()
    return {"status": "ok"}


@api.get("/orgs/me")
async def org_me(
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    org = await session.get(Org, principal.org_id)
    if org is None:
        raise ApiError(404, "NOT_FOUND", "organisation not found")
    return {
        "id": str(org.id),
        "name": org.name,
        "region": org.region,
        "deployment": org.deployment,
        "quota_concurrent_jobs": org.quota_concurrent_jobs,
        "role": principal.role,
    }


async def _scenario_for(
    session: AsyncSession, principal: Principal, scenario_id: uuid.UUID
) -> Scenario:
    scenario = await session.get(Scenario, scenario_id)
    if scenario is None or scenario.is_deleted:
        raise ApiError(404, "NOT_FOUND", "scenario not found")
    if scenario.org_id != principal.org_id:
        raise ApiError(403, "FORBIDDEN", "scenario belongs to another organisation")
    return scenario


@api.post("/scenarios", status_code=201)
async def create_scenario(
    body: ScenarioCreate,
    principal: Principal = Depends(
        require_roles("researcher", "scenario_owner", "org_admin")
    ),
    session: AsyncSession = Depends(get_session),
    idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
) -> Any:
    replay = await replay_idempotent(
        session, principal, idempotency_key, "POST", "/api/v1/scenarios"
    )
    if replay is not None:
        status_code, replay_payload = replay
        return JSONResponse(status_code=status_code, content=replay_payload)
    spec_sha = _validate_spec(body.spec)
    scenario = Scenario(
        org_id=principal.org_id,
        template_key=body.template_key,
        name=body.name,
        description=body.description,
        spec=body.spec,
        created_by=principal.user_id,
    )
    session.add(scenario)
    await session.flush()
    response_payload: dict[str, Any] = {
        "data": {
            "id": str(scenario.id),
            "version": scenario.version,
            "spec_sha256": spec_sha,
        }
    }
    await save_idempotent(
        session, principal, idempotency_key, "POST", "/api/v1/scenarios", 201, response_payload
    )
    await session.commit()
    return JSONResponse(status_code=201, content=response_payload)


@api.get("/scenarios")
async def list_scenarios(
    principal: Principal = Depends(
        require_roles("researcher", "scenario_owner", "org_admin", "analyst")
    ),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    rows = (
        await session.scalars(
            select(Scenario).where(
                Scenario.org_id == principal.org_id, Scenario.is_deleted.is_(False)
            )
        )
    ).all()
    return {"data": [{"id": str(row.id), "name": row.name, "version": row.version} for row in rows]}


@api.get("/scenarios/{scenario_id}")
async def get_scenario(
    scenario_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    scenario = await _scenario_for(session, principal, scenario_id)
    return {
        "data": {
            "id": str(scenario.id),
            "name": scenario.name,
            "version": scenario.version,
            "spec": scenario.spec,
        }
    }


@api.patch("/scenarios/{scenario_id}")
async def patch_scenario(
    scenario_id: uuid.UUID,
    body: ScenarioPatch,
    principal: Principal = Depends(
        require_roles("researcher", "scenario_owner", "org_admin")
    ),
    session: AsyncSession = Depends(get_session),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    if not if_match:
        raise ApiError(428, "IF_MATCH_REQUIRED", "If-Match header is required")
    scenario = await _scenario_for(session, principal, scenario_id)
    if principal.role == "researcher" and scenario.created_by != principal.user_id:
        raise ApiError(403, "FORBIDDEN", "researchers may only edit their own scenarios")
    try:
        expected = int(if_match.strip('"'))
    except ValueError as exc:
        raise ApiError(400, "INVALID_IF_MATCH", "If-Match must be a version number") from exc
    if expected != scenario.version:
        raise ApiError(
            409, "VERSION_CONFLICT", "scenario was modified", {"current": scenario.version}
        )
    if body.name is not None:
        scenario.name = body.name
    if body.description is not None:
        scenario.description = body.description
    if body.spec is not None:
        _validate_spec(body.spec)
        scenario.spec = body.spec
    scenario.version += 1
    scenario.updated_at = utcnow()
    await session.commit()
    return {"data": {"id": str(scenario.id), "version": scenario.version}}


@api.delete("/scenarios/{scenario_id}", status_code=204)
async def delete_scenario(
    scenario_id: uuid.UUID,
    principal: Principal = Depends(
        require_roles("researcher", "scenario_owner", "org_admin")
    ),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    scenario = await _scenario_for(session, principal, scenario_id)
    if principal.role == "researcher" and scenario.created_by != principal.user_id:
        raise ApiError(403, "FORBIDDEN", "researchers may only delete their own scenarios")
    scenario.is_deleted = True
    await session.commit()
    return JSONResponse(status_code=204, content=None)


@api.delete("/datasets/{dataset_id}", status_code=204)
async def delete_dataset(
    dataset_id: uuid.UUID,
    principal: Principal = Depends(require_roles("scenario_owner", "org_admin")),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    dataset = await session.get(Dataset, dataset_id)
    if dataset is None:
        raise ApiError(404, "NOT_FOUND", "dataset not found")
    if dataset.org_id != principal.org_id:
        raise ApiError(403, "FORBIDDEN", "dataset belongs to another organisation")
    await session.delete(dataset)
    await write_audit(session, principal, "dataset.delete", str(dataset_id))
    await session.commit()
    return JSONResponse(status_code=204, content=None)


@api.post("/runs", status_code=201)
async def create_run(
    body: RunCreate,
    principal: Principal = Depends(
        require_roles("researcher", "scenario_owner", "org_admin")
    ),
    session: AsyncSession = Depends(get_session),
    idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
) -> Any:
    replay = await replay_idempotent(
        session, principal, idempotency_key, "POST", "/api/v1/runs"
    )
    if replay is not None:
        status_code, replay_payload = replay
        return JSONResponse(status_code=status_code, content=replay_payload)
    scenario = await _scenario_for(session, principal, body.scenario_id)
    repeats = body.repeats or 1
    seed = body.seed if body.seed is not None else 42
    spec_sha = hashlib.sha256(json.dumps(scenario.spec, sort_keys=True).encode()).hexdigest()
    run = Run(
        org_id=principal.org_id,
        scenario_id=scenario.id,
        run_id_external=f"{spec_sha[:16]}-{seed}",
        status="queued",
        spec_sha256=spec_sha,
        manifest={"seed": seed, "repeats": repeats},
        repeats=repeats,
        created_by=principal.user_id,
    )
    session.add(run)
    await session.flush()
    await write_audit(
        session, principal, "run.create", str(run.id), {"scenario_id": str(scenario.id)}
    )
    result_payload = {
        "data": {
            "id": str(run.id),
            "status": run.status,
            "run_id_external": run.run_id_external,
        }
    }
    await save_idempotent(
        session, principal, idempotency_key, "POST", "/api/v1/runs", 201, result_payload
    )
    await session.commit()
    return JSONResponse(status_code=201, content=result_payload)


async def _visible_run(
    session: AsyncSession, principal: Principal, run_id: uuid.UUID
) -> Run:
    run = await session.get(Run, run_id)
    if run is None:
        raise ApiError(404, "NOT_FOUND", "run not found")
    if run.org_id != principal.org_id:
        raise ApiError(403, "FORBIDDEN", "run belongs to another organisation")
    if principal.role == "reviewer":
        share = await session.scalar(
            select(RunShare).where(
                RunShare.run_id == run_id, RunShare.user_id == principal.user_id
            )
        )
        if share is None:
            raise ApiError(403, "FORBIDDEN", "run is not shared with this reviewer")
    return run


@api.get("/runs/{run_id}")
async def get_run(
    run_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    run = await _visible_run(session, principal, run_id)
    return {"data": {"id": str(run.id), "status": run.status, "repeats": run.repeats}}


@api.get("/runs")
async def list_runs(
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    if principal.role == "reviewer":
        shared = await session.scalars(
            select(RunShare.run_id).where(RunShare.user_id == principal.user_id)
        )
        ids = list(shared)
        rows = (
            await session.scalars(
                select(Run).where(Run.id.in_(ids), Run.org_id == principal.org_id)
            )
        ).all()
    else:
        rows = (
            await session.scalars(select(Run).where(Run.org_id == principal.org_id))
        ).all()
    return {"data": [{"id": str(row.id), "status": row.status} for row in rows]}


@api.get("/runs/{run_id}/nodes/{node_id}/trace")
async def node_trace(run_id: uuid.UUID, node_id: int) -> JSONResponse:
    raise ApiError(
        403, "NODE_TRACE_FORBIDDEN", "single-node opinion traces are forbidden by policy"
    )


@api.post("/reports/{run_id}/export")
async def export_report(
    run_id: uuid.UUID,
    detail: bool = False,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    run = await _visible_run(session, principal, run_id)
    if principal.role == "reviewer" and detail:
        raise ApiError(403, "DETAIL_FORBIDDEN", "reviewers may export summaries only")
    await write_audit(
        session, principal, "report.export", str(run.id), {"detail": detail}
    )
    await session.commit()
    return {"data": {"run_id": str(run.id), "detail": detail, "status": "queued"}}


@api.post("/admin/settings")
async def admin_settings(
    principal: Principal = Depends(require_roles("org_admin")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    await write_audit(session, principal, "settings.change", str(principal.org_id))
    await session.commit()
    return {"data": {"status": "ok"}}


app.include_router(auth)
app.include_router(api)
