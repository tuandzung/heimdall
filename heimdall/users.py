from __future__ import annotations

import logging
import uuid

from typing import TYPE_CHECKING, AsyncGenerator, Optional

from fastapi import Depends, Request, Response
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users.manager import BaseUserManager, UUIDIDMixin
from httpx_oauth.clients.google import GoogleOAuth2

from .config import AppConfig
from .db import User, get_user_db

if TYPE_CHECKING:
    from fastapi_users.db import (
        SQLAlchemyUserDatabase,
    )
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("uvicorn.error")


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = "heimdall-reset"
    verification_token_secret = "heimdall-verify"

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        logger.info(f"User {user.email} has registered.")

    async def on_after_login(self, user: User, request: Optional[Request] = None, response: Optional[Response] = None):
        logger.info(f"User {user.email} has login.")


def get_bearer_transport(settings: AppConfig) -> BearerTransport:
    # JWT Bearer transport; interactive docs use tokenUrl for Authorize button
    return BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy(settings: AppConfig) -> JWTStrategy:
    secret = settings.auth.session_secret_key or "change-me"
    return JWTStrategy(secret=secret, lifetime_seconds=3600)


def get_auth_backend(settings: AppConfig) -> AuthenticationBackend:
    bearer_transport = get_bearer_transport(settings)
    return AuthenticationBackend(
        name="jwt",
        transport=bearer_transport,
        get_strategy=lambda: get_jwt_strategy(settings),
    )


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
) -> AsyncGenerator[UserManager, None]:
    yield UserManager(user_db)


def build_fastapi_users(
    settings: AppConfig,
) -> tuple[FastAPIUsers[User, uuid.UUID], AuthenticationBackend, GoogleOAuth2, async_sessionmaker[AsyncSession]]:
    auth_backend = get_auth_backend(settings)
    fusers = FastAPIUsers[User, uuid.UUID](
        get_user_manager,
        [auth_backend],
    )
    google_client = GoogleOAuth2(settings.auth.google_client_id or "", settings.auth.google_client_secret or "")
    # Session maker will be created on demand in init
    return fusers, auth_backend, google_client, None  # type: ignore[return-value]


# Pre-instantiate for importers that do not want to handle DI
settings = AppConfig()

fusers, auth_backend, google_client, _ = build_fastapi_users(settings)
current_active_user = fusers.current_user(active=True)
