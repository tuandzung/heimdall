from __future__ import annotations

import uuid

from typing import TYPE_CHECKING, AsyncGenerator, Optional

from fastapi import Depends, Request, Response
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, CookieTransport, JWTStrategy
from fastapi_users.manager import BaseUserManager, UUIDIDMixin
from httpx_oauth.clients.google import GoogleOAuth2

from .config import AppConfig
from .db import User, get_user_db
from .logger import logger

if TYPE_CHECKING:
    from fastapi_users.db import (
        SQLAlchemyUserDatabase,
    )
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from .models import UserCreate


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = "heimdall-reset"
    verification_token_secret = "heimdall-verify"

    def __init__(self, user_db, settings: AppConfig | None = None):
        super().__init__(user_db)
        self.settings = settings or AppConfig()

    async def validate_email_domain(self, email: str) -> None:
        """Validate email/domain restrictions for OAuth authentication."""
        from fastapi_users import InvalidPasswordException

        # Check if email is in allowed emails list
        if self.settings.auth.allowed_emails and email in self.settings.auth.allowed_emails:
            # Email is explicitly allowed, no further checks needed
            return
        elif self.settings.auth.allowed_domains:
            # Check if domain is in allowed domains list
            domain = email.split("@")[-1] if "@" in email else ""
            if domain not in self.settings.auth.allowed_domains:
                raise InvalidPasswordException(reason="Email address is not allowed for registration")
        elif self.settings.auth.allowed_emails:
            # Only allowed emails are configured and this email is not in the list
            raise InvalidPasswordException(reason="Email address is not allowed for registration")

    async def validate_password(
        self,
        password: str,
        user: UserCreate | User,
    ) -> None:
        """Validate password and email/domain restrictions."""
        from fastapi_users import InvalidPasswordException

        # First validate the email/domain restrictions
        email = user.email

        await self.validate_email_domain(email)

        # You can add additional password validation here if needed
        if len(password) < 8:
            raise InvalidPasswordException(reason="Password should be at least 8 characters")

    async def oauth_callback(
        self,
        oauth_name: str,
        access_token: str,
        account_id: str,
        account_email: str,
        expires_at: Optional[int] = None,
        refresh_token: Optional[str] = None,
        request: Optional[Request] = None,
        *,
        associate_by_email: bool = False,
        is_verified_by_default: bool = False,
    ) -> User:
        """Handle OAuth callback with email/domain validation."""
        # Validate email/domain restrictions before proceeding
        await self.validate_email_domain(account_email)

        # Call the parent implementation
        return await super().oauth_callback(
            oauth_name=oauth_name,
            access_token=access_token,
            account_id=account_id,
            account_email=account_email,
            expires_at=expires_at,
            refresh_token=refresh_token,
            request=request,
            associate_by_email=associate_by_email,
            is_verified_by_default=is_verified_by_default,
        )

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        logger.info(f"User {user.email} has registered.")

    async def on_after_login(self, user: User, request: Optional[Request] = None, response: Optional[Response] = None):
        logger.info(f"User {user.email} has login.")


def get_jwt_strategy(settings: AppConfig) -> JWTStrategy:
    secret = settings.auth.session_secret_key or "change-me"
    return JWTStrategy(secret=secret, lifetime_seconds=3600)


def get_cookie_transport(settings: AppConfig) -> CookieTransport:
    return CookieTransport(
        cookie_name=settings.auth.cookie_name,
        cookie_max_age=settings.auth.cookie_max_age,
        cookie_path=settings.auth.cookie_path,
        cookie_secure=settings.auth.cookie_secure,
        cookie_httponly=settings.auth.cookie_httponly,
        cookie_samesite=settings.auth.cookie_samesite,
    )


def get_cookie_auth_backend(settings: AppConfig) -> AuthenticationBackend:
    cookie_transport = get_cookie_transport(settings)
    return AuthenticationBackend(
        name="cookie",
        transport=cookie_transport,
        get_strategy=lambda: get_jwt_strategy(settings),
    )


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
    settings: AppConfig = Depends(lambda: AppConfig()),
) -> AsyncGenerator[UserManager, None]:
    yield UserManager(user_db, settings)


def build_fastapi_users(
    settings: AppConfig,
) -> tuple[
    FastAPIUsers[User, uuid.UUID],
    AuthenticationBackend,
    GoogleOAuth2,
    async_sessionmaker[AsyncSession],
]:
    cookie_backend = get_cookie_auth_backend(settings)
    fusers = FastAPIUsers[User, uuid.UUID](
        get_user_manager,
        [cookie_backend],
    )
    google_client = GoogleOAuth2(settings.auth.google_client_id or "", settings.auth.google_client_secret or "")
    # Session maker will be created on demand in init
    return fusers, cookie_backend, google_client, None  # type: ignore[return-value]


# Pre-instantiate for importers that do not want to handle DI
settings = AppConfig()

fusers, cookie_backend, google_client, _ = build_fastapi_users(settings)
current_active_user = fusers.current_user(active=True)
