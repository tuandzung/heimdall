from __future__ import annotations

import time

from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import __version__
from .config import AppConfig
from .models import FlinkJob, UserRead, UserUpdate
from .service import FlinkJobLocator, K8sOperatorFlinkJobLocator
from .users import auth_backend, current_active_user, fusers, google_client

if TYPE_CHECKING:
    from .db import User


@lru_cache
def get_settings() -> AppConfig:
    return AppConfig()


settings = get_settings()

webui_dist = Path(__file__).resolve().parent.parent / "webui" / "dist"
templates = Jinja2Templates(directory=webui_dist)


def get_job_locator(settings: AppConfig = Depends(get_settings)) -> FlinkJobLocator:
    if settings.joblocator.k8s_operator.enabled:
        return K8sOperatorFlinkJobLocator(settings)
    # In future, support more strategies; for now return empty impl
    return K8sOperatorFlinkJobLocator(settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Not needed if you setup a migration system like Alembic
    settings = get_settings()
    if settings.auth.enabled:
        from .db import create_db_and_tables  # local import

        await create_db_and_tables(settings)
    yield


app = FastAPI(title="Heimdall", version=__version__, lifespan=lifespan)


# OAuth router under /auth/google (uses JWT backend)
app.include_router(
    fusers.get_oauth_router(
        google_client,
        auth_backend,
        settings.auth.session_secret_key or "change-me",
        is_verified_by_default=True,
        associate_by_email=True,
        redirect_url=settings.auth.redirect_url,
    ),
    dependencies=[Depends(get_settings)],
    prefix="/auth/google",
    tags=["auth"],
)
# JWT Login endpoints (username/password) – optional but useful for API clients
app.include_router(fusers.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"])
app.include_router(
    fusers.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)


@app.get("/auth/callback")
async def auth_callback(request: Request):
    return templates.TemplateResponse(request, "auth-callback.html")


@app.get("/api/config")
def read_config(
    settings: AppConfig = Depends(get_settings),
    _: User = Depends(current_active_user if settings.auth.enabled else lambda: None),
):
    return {
        "appVersion": settings.resolved_app_version(__version__),
        "patterns": settings.patterns,
        "endpointPathPatterns": settings.endpoint_path_patterns,
    }


_jobs_cache_value: list[FlinkJob] | None = None
_jobs_cache_ts: float | None = None


@app.get("/api/jobs", response_model=list[FlinkJob])
async def list_jobs(
    locator: FlinkJobLocator = Depends(get_job_locator),
    settings: AppConfig = Depends(get_settings),
    _: User = Depends(current_active_user if settings.auth.enabled else lambda: None),
):
    global _jobs_cache_value, _jobs_cache_ts
    now = time.time()
    ttl = max(0, int(settings.jobs_cache_ttl))
    if _jobs_cache_value is not None and _jobs_cache_ts is not None and (now - _jobs_cache_ts) < ttl:
        return _jobs_cache_value

    # Fully async path
    result = await locator.find_all()
    _jobs_cache_value = result
    _jobs_cache_ts = now
    return result


@app.get("/healthz")
async def healthz():
    return {"ok": True}


# Mount built UI last so it doesn't shadow /auth/* routes
app.mount("/", StaticFiles(directory=str(webui_dist), html=True), name="ui")
