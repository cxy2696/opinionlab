"""FastAPI application: auth, RBAC, tenant isolation and audit ()."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.demo import WEB_DIR
from app.demo import router as demo_router
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
from app.locks import acquire_ingest_lock
from app.models import (
    Artifact,
    Dataset,
    GraphSnapshot,
    Membership,
    Org,
    RefreshToken,
    Run,
    RunShare,
    Scenario,
    UseCaseApproval,
    User,
    utcnow,
)
from app.observability import ObservabilityMiddleware, metrics_payload
from app.progress import get_progress, set_progress
from app.quota import check_quota, estimate_seconds
from app.ratelimit import RateLimitMiddleware
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.settings import settings
from app.state import request_cancel
from hnle.spec import ModelSpec

app = FastAPI(title="OpinionLab API", version="1.3.1")
app.add_exception_handler(ApiError, api_error_handler)  # type: ignore[arg-type]
app.add_middleware(RateLimitMiddleware)

api = APIRouter(prefix="/api/v1")
auth = APIRouter(prefix="/api/v1/auth")


app.add_middleware(ObservabilityMiddleware)


@app.get("/metrics")
async def metrics() -> Response:
    payload, media_type = metrics_payload()
    return Response(content=payload, media_type=media_type)


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
    model_config = {
        "json_schema_extra": {
            "example": {"email": "analyst@example.com", "password": "Secret123!"}
        }
    }

    email: str
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=128)


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
    model_config = {
        "json_schema_extra": {
            "example": {
                "scenario_id": "0f8fad5b-d9cb-469f-a165-70867728950e",
                "repeats": 50,
                "seed": 42,
                "confirm": False,
            }
        }
    }

    scenario_id: uuid.UUID
    repeats: int | None = Field(default=None, ge=1, le=500)
    seed: int | None = Field(default=None, ge=0)
    confirm: bool = False


class DatasetCreate(BaseModel):
    name: str
    source_type: str = "upload_csv"
    size_bytes: int | None = Field(default=None, ge=0)
    consent_basis: str | None = None
    dpia: dict[str, Any] | None = None


class UseCaseRequest(BaseModel):
    template_key: str
    declaration: str = Field(min_length=10, max_length=4000)


class CompareRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "run_ids": [
                    "0f8fad5b-d9cb-469f-a165-70867728950e",
                    "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
                ]
            }
        }
    }

    run_ids: list[uuid.UUID] = Field(min_length=2, max_length=10)


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


@auth.post(
    "/login",
    response_model=TokenPair,
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOi...",
                        "refresh_token": "eyJhbGciOi...",
                        "token_type": "bearer",
                    }
                }
            }
        }
    },
)
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


@auth.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    user = await session.get(User, principal.user_id)
    if user is None or not verify_password(user.password_hash, body.old_password):
        raise ApiError(401, "INVALID_CREDENTIALS", "current password is incorrect")
    from app.security import hash_password

    user.password_hash = hash_password(body.new_password)
    user.must_change_pw = False
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


@api.post("/datasets", status_code=201)
async def create_dataset(
    body: DatasetCreate,
    principal: Principal = Depends(
        require_roles("researcher", "analyst", "scenario_owner", "org_admin")
    ),
    session: AsyncSession = Depends(get_session),
    idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
) -> Any:
    replay = await replay_idempotent(
        session, principal, idempotency_key, "POST", "/api/v1/datasets"
    )
    if replay is not None:
        status_code, replay_payload = replay
        return JSONResponse(status_code=status_code, content=replay_payload)
    dataset = Dataset(
        org_id=principal.org_id,
        name=body.name,
        source_type=body.source_type,
        consent_basis=body.consent_basis,
        dpia=body.dpia,
    )
    session.add(dataset)
    await session.flush()
    response_payload: dict[str, Any] = {
        "data": {"id": str(dataset.id), "upload_url": f"/uploads/{dataset.id}"}
    }
    await save_idempotent(
        session, principal, idempotency_key, "POST", "/api/v1/datasets", 201, response_payload
    )
    await session.commit()
    return JSONResponse(status_code=201, content=response_payload)


@api.get("/datasets")
async def list_datasets(
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    rows = (
        await session.scalars(select(Dataset).where(Dataset.org_id == principal.org_id))
    ).all()
    return {"data": [{"id": str(row.id), "name": row.name} for row in rows]}


async def _dataset_for(
    session: AsyncSession, principal: Principal, dataset_id: uuid.UUID
) -> Dataset:
    dataset = await session.get(Dataset, dataset_id)
    if dataset is None:
        raise ApiError(404, "NOT_FOUND", "dataset not found")
    if dataset.org_id != principal.org_id:
        raise ApiError(403, "FORBIDDEN", "dataset belongs to another organisation")
    return dataset


@api.get("/datasets/{dataset_id}")
async def get_dataset(
    dataset_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    dataset = await _dataset_for(session, principal, dataset_id)
    return {"data": {"id": str(dataset.id), "name": dataset.name}}


@api.post("/datasets/{dataset_id}/ingest", status_code=202)
async def ingest_dataset(
    dataset_id: uuid.UUID,
    principal: Principal = Depends(
        require_roles("researcher", "analyst", "scenario_owner", "org_admin")
    ),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    dataset = await _dataset_for(session, principal, dataset_id)
    if not acquire_ingest_lock(str(dataset.id)):
        raise ApiError(409, "INGEST_IN_PROGRESS", "dataset is already being ingested")
    return {"data": {"dataset_id": str(dataset.id), "status": "queued"}}


@api.get("/templates")
async def list_templates(
    principal: Principal = Depends(get_principal),
) -> dict[str, Any]:
    from hnle.templates import iter_templates

    payload = [
        {
            "key": template.key,
            "name_zh": template.name_zh,
            "name_en": template.name_en,
            "enabled": template.is_enabled(),
        }
        for template in iter_templates("scenarios")
    ]
    return {"data": payload}


@api.post("/templates/{key}/clone", status_code=201)
async def clone_template(
    key: str,
    principal: Principal = Depends(
        require_roles("researcher", "scenario_owner", "org_admin")
    ),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    from hnle.templates import iter_templates

    match = next(
        (template for template in iter_templates("scenarios") if template.key == key), None
    )
    if match is None:
        raise ApiError(404, "NOT_FOUND", "template not found")
    approval = await session.scalar(
        select(UseCaseApproval).where(
            UseCaseApproval.org_id == principal.org_id,
            UseCaseApproval.template_key == key,
            UseCaseApproval.status == "approved",
        )
    )
    if (
        not match.is_enabled()
        and settings.use_case_review_enabled
        and approval is None
    ):
        raise ApiError(
            403,
            "USE_CASE_NOT_APPROVED",
            "G5-class templates require use-case approval before cloning",
        )
    scenario = Scenario(
        org_id=principal.org_id,
        template_key=key,
        name=match.name_en,
        spec=match.spec.model_dump(mode="json"),
        created_by=principal.user_id,
    )
    session.add(scenario)
    await session.flush()
    await session.commit()
    return {"data": {"id": str(scenario.id), "template_key": key}}


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
    scenarios = (
        await session.scalars(select(Scenario).where(Scenario.dataset_id == dataset_id))
    ).all()
    for scenario in scenarios:
        runs = (await session.scalars(select(Run).where(Run.scenario_id == scenario.id))).all()
        for run in runs:
            await session.execute(delete(Artifact).where(Artifact.run_id == run.id))
            await session.execute(delete(RunShare).where(RunShare.run_id == run.id))
            await session.delete(run)
        scenario.dataset_id = None
    await session.execute(delete(GraphSnapshot).where(GraphSnapshot.dataset_id == dataset_id))
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
    active = await session.scalar(
        select(func.count())
        .select_from(Run)
        .where(
            Run.org_id == principal.org_id,
            Run.status.in_(["queued", "running", "cancelling"]),
        )
    )
    org = await session.get(Org, principal.org_id)
    limit = org.quota_concurrent_jobs if org is not None else 4
    steps_value = (scenario.spec or {}).get("n_steps", 1000)
    n_steps = int(str(steps_value))
    estimate = estimate_seconds(nnz=n_steps * 100, n_steps=n_steps, repeats=repeats)
    check_quota(int(active or 0), limit, estimate, confirmed=body.confirm)
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
    set_progress(str(run.id), 0, repeats)
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
    return {
        "data": {
            "id": str(run.id),
            "status": run.status,
            "repeats": run.repeats,
            "done_replicas": run.done_replicas,
            "progress": get_progress(str(run.id)),
        }
    }


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


@api.get(
    "/runs/{run_id}/metrics",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "data": {
                            "run_id": "0f8fad5b-d9cb-469f-a165-70867728950e",
                            "status": "succeeded",
                            "aggregate": {
                                "diversity_final": {
                                    "mean": 0.11,
                                    "ci95_lo": 0.06,
                                    "ci95_hi": 0.16,
                                    "n": 50,
                                }
                            },
                            "disclaimer_key": "simulation_not_prediction",
                        }
                    }
                }
            }
        }
    },
)
async def run_metrics(
    run_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    run = await _visible_run(session, principal, run_id)
    return {
        "data": {
            "run_id": str(run.id),
            "status": run.status,
            "aggregate": run.aggregate or {},
            "disclaimer_key": run.disclaimer_key,
        }
    }


@api.get("/runs/{run_id}/artifacts")
async def run_artifacts(
    run_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    run = await _visible_run(session, principal, run_id)
    return {"data": [], "run_id": str(run.id)}


@api.post("/runs/{run_id}/cancel", status_code=202)
async def cancel_run(
    run_id: uuid.UUID,
    principal: Principal = Depends(
        require_roles("researcher", "scenario_owner", "org_admin")
    ),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    run = await _visible_run(session, principal, run_id)
    if principal.role == "researcher" and run.created_by != principal.user_id:
        raise ApiError(403, "FORBIDDEN", "researchers may only cancel their own runs")
    new_status, accepted = request_cancel(run.status, run.done_replicas, run.repeats)
    if not accepted:
        raise ApiError(409, "INVALID_STATE", f"run is {run.status}")
    run.status = new_status
    await write_audit(session, principal, "run.cancel", str(run.id))
    await session.commit()
    return {"data": {"id": str(run.id), "status": new_status}}


@api.post("/compare", status_code=202)
async def compare_runs(
    body: CompareRequest,
    principal: Principal = Depends(
        require_roles("researcher", "scenario_owner", "org_admin")
    ),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    runs = []
    for run_id in body.run_ids:
        runs.append(await _visible_run(session, principal, run_id))
    return {
        "data": {
            "run_ids": [str(run.id) for run in runs],
            "status": "queued",
            "direction": "inconclusive",
        }
    }


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
    return {
        "data": {
            "run_id": str(run.id),
            "detail": detail,
            "status": "queued",
            "disclaimer_key": run.disclaimer_key,
            "watermark": not detail,
            "summary_only": principal.role == "reviewer" or not detail,
        }
    }


@api.post("/orgs/use-case", status_code=201)
async def request_use_case(
    body: UseCaseRequest,
    principal: Principal = Depends(require_roles("org_admin")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    org = await session.get(Org, principal.org_id)
    if org is not None:
        org.use_case_declaration = body.declaration
    approval = await session.scalar(
        select(UseCaseApproval).where(
            UseCaseApproval.org_id == principal.org_id,
            UseCaseApproval.template_key == body.template_key,
        )
    )
    if approval is None:
        approval = UseCaseApproval(
            org_id=principal.org_id,
            template_key=body.template_key,
            declaration=body.declaration,
            requested_by=principal.user_id,
        )
        session.add(approval)
    else:
        approval.declaration = body.declaration
        approval.status = "pending"
    await session.flush()
    await session.commit()
    return {"data": {"approval_id": str(approval.id), "status": approval.status}}


@api.post("/platform/use-cases/{approval_id}/approve")
async def approve_use_case(
    approval_id: uuid.UUID,
    principal: Principal = Depends(require_roles("platform_admin")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    approval = await session.get(UseCaseApproval, approval_id)
    if approval is None:
        raise ApiError(404, "NOT_FOUND", "approval not found")
    approval.status = "approved"
    approval.approved_by = principal.user_id
    approval.decided_at = utcnow()
    await write_audit(
        session, principal, "use_case.approve", str(approval.id), {"org_id": str(approval.org_id)}
    )
    await session.commit()
    return {"data": {"approval_id": str(approval.id), "status": "approved"}}


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
app.include_router(demo_router)
app.mount("/api/v1/demo/static", StaticFiles(directory=WEB_DIR), name="demo-static")


@app.get("/")
async def root() -> RedirectResponse:
    return RedirectResponse(url="/api/v1/demo/app")
