from __future__ import annotations

import time

from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse

from . import __version__
from .config import AppConfig
from .models import FlinkJob
from .service import FlinkJobLocator, K8sOperatorFlinkJobLocator


@lru_cache
def get_settings() -> AppConfig:
    return AppConfig()


def get_job_locator(settings: AppConfig = Depends(get_settings)) -> FlinkJobLocator:
    if settings.joblocator.k8s_operator.enabled:
        return K8sOperatorFlinkJobLocator(settings)
    # In future, support more strategies; for now return empty impl
    return K8sOperatorFlinkJobLocator(settings)


app = FastAPI(title="Heimdall", version=__version__)


def _require_authenticated_user(request: Request, settings: AppConfig = Depends(get_settings)) -> None:
    if settings.auth.enabled:
        user = request.session.get("user") if hasattr(request, "session") else None
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/api/config")
def read_config(
    settings: AppConfig = Depends(get_settings),
    _: None = Depends(_require_authenticated_user),
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
    _: None = Depends(_require_authenticated_user),
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


# Allow CORS if needed (for alternate deployments); otherwise static mount will share origin
settings_for_cors = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings_for_cors.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sessions (for OAuth)
if settings_for_cors.auth.session_secret_key:
    app.add_middleware(SessionMiddleware, secret_key=settings_for_cors.auth.session_secret_key)

# --- OAuth with Google ---
try:
    from authlib.integrations.starlette_client import OAuth
except Exception:  # pragma: no cover
    OAuth = None  # type: ignore


def _ensure_oauth(settings: AppConfig) -> "OAuth":
    if OAuth is None:
        raise RuntimeError("authlib is not installed")
    oauth = OAuth()
    oauth.register(
        name="google",
        client_id=settings.auth.google_client_id,
        client_secret=settings.auth.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    return oauth


def _is_email_allowed(settings: AppConfig, email: str | None) -> bool:
    if not email:
        return False
    if settings.auth.allowed_emails and email in settings.auth.allowed_emails:
        return True
    if settings.auth.allowed_domains:
        domain = email.split("@")[-1]
        return domain in settings.auth.allowed_domains
    # If no allowlist configured, allow all
    return not (settings.auth.allowed_emails or settings.auth.allowed_domains)


@app.get("/auth/login")
async def auth_login(request: Request):
    settings = get_settings()
    if not settings.auth.enabled:
        raise HTTPException(status_code=404, detail="Auth disabled")
    oauth = _ensure_oauth(settings)
    redirect_uri = settings.auth.redirect_url or str(request.url_for("auth_callback"))
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/callback")
async def auth_callback(request: Request):
    settings = get_settings()
    if not settings.auth.enabled:
        raise HTTPException(status_code=404, detail="Auth disabled")
    oauth = _ensure_oauth(settings)
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo") or {}
    email = userinfo.get("email")
    if not _is_email_allowed(settings, email):
        raise HTTPException(status_code=403, detail="Forbidden")
    request.session["user"] = {
        "email": email,
        "name": userinfo.get("name"),
        "picture": userinfo.get("picture"),
    }
    # Redirect to UI root
    return RedirectResponse(url="/")


@app.get("/auth/me")
async def auth_me(request: Request):
    user = request.session.get("user") if hasattr(request, "session") else None
    return {"user": user}


@app.post("/auth/logout")
async def auth_logout(request: Request):
    if hasattr(request, "session"):
        request.session.clear()
    return {"ok": True}


@app.get("/healthz")
async def healthz():
    return {"ok": True}


# Mount built UI if present (must be last so it doesn't shadow /auth/* routes)
webui_dist = Path(__file__).resolve().parent.parent / "webui" / "dist"
if webui_dist.exists():
    app.mount("/", StaticFiles(directory=str(webui_dist), html=True), name="ui")
