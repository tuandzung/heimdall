from __future__ import annotations

import time

from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

from fastapi import Depends, FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask

from . import __version__
from .config import AppConfig
from .models import FlinkJob, UserRead, UserUpdate
from .service import FlinkJobLocator, K8sOperatorFlinkJobLocator
from .users import cookie_backend, current_active_user, fusers, google_client

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
    # Shared HTTP client for proxying
    app.state.http_client = httpx.AsyncClient()
    if settings.auth.enabled:
        from .db import create_db_and_tables  # local import

        await create_db_and_tables(settings)
    try:
        yield
    finally:
        await app.state.http_client.aclose()


app = FastAPI(title="Heimdall", version=__version__, lifespan=lifespan)


# Cookie-based OAuth router under /auth/google-cookie
app.include_router(
    fusers.get_oauth_router(
        google_client,
        cookie_backend,
        settings.auth.session_secret_key or "change-me",
        is_verified_by_default=True,
        associate_by_email=True,
        redirect_url=settings.auth.redirect_url,
    ),
    dependencies=[Depends(get_settings)],
    prefix="/auth/google-cookie",
    tags=["auth"],
)
# Cookie login endpoints (username/password)
app.include_router(fusers.get_auth_router(cookie_backend), prefix="/auth/cookie", tags=["auth"])
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


@app.api_route("/proxy/{app}/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
async def flink_rest_proxy(
    app: str,
    full_path: str,
    request: Request,
    settings: AppConfig = Depends(get_settings),
    _: User = Depends(current_active_user if settings.auth.enabled else lambda: None),
):
    # Resolve base URL for this app from mapping, fallback to default
    base = settings.proxy_target_map.get(app) or f"http://{app}-rest:8081"
    target_url = f"{base.rstrip('/')}/{full_path}"

    client: httpx.AsyncClient = request.app.state.http_client

    # Prepare proxied request
    method = request.method
    # Forward query params
    query_string = request.url.query
    if query_string:
        target_url = f"{target_url}?{query_string}"

    # Forward headers except host-related hop-by-hop ones
    hop_by_hop = {
        "host",
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    }
    headers = {k: v for k, v in request.headers.items() if k.lower() not in hop_by_hop}

    # Body streaming
    async def body_iter():
        async for chunk in request.stream():
            yield chunk

    req = client.build_request(method, target_url, headers=headers, content=body_iter())
    resp = await client.send(req, stream=True)

    # Streaming response back to client
    def iter_response():
        return resp.aiter_raw()

    # Filter response headers
    excluded_resp_headers = {"content-encoding", "transfer-encoding", "connection"}
    response_headers = [(k, v) for k, v in resp.headers.items() if k.lower() not in excluded_resp_headers]

    return StreamingResponse(
        iter_response(),
        status_code=resp.status_code,
        headers=dict(response_headers),
        background=BackgroundTask(resp.aclose),
    )


# Mount built UI last so it doesn't shadow /auth/* routes
app.mount("/", StaticFiles(directory=str(webui_dist), html=True), name="ui")
