from __future__ import annotations

from typing import TYPE_CHECKING, AsyncGenerator, Optional

from fastapi import Depends
from fastapi_users.db import (
    SQLAlchemyBaseOAuthAccountTableUUID,
    SQLAlchemyBaseUserTableUUID,
    SQLAlchemyUserDatabase,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, relationship

if TYPE_CHECKING:
    from .config import AppConfig


class Base(DeclarativeBase):
    pass


class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):  # type: ignore[misc]
    __tablename__ = "oauth_account"


class User(SQLAlchemyBaseUserTableUUID, Base):  # type: ignore[misc]
    __tablename__ = "user"
    oauth_accounts: Mapped[list[OAuthAccount]] = relationship(
        "OAuthAccount", lazy="joined", cascade="all, delete-orphan"
    )


_engine: Optional[object] = None
_async_session_maker: Optional[async_sessionmaker[AsyncSession]] = None


async def get_async_sessionmaker(settings: AppConfig) -> async_sessionmaker[AsyncSession]:
    global _engine, _async_session_maker
    if _async_session_maker is None:
        _engine = create_async_engine(settings.auth.database_url, future=True, echo=False)
        _async_session_maker = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)
    return _async_session_maker


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    assert _async_session_maker is not None
    async with _async_session_maker() as session:  # type: ignore[misc]
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User, OAuthAccount)


async def create_db_and_tables(settings: AppConfig) -> None:
    await get_async_sessionmaker(settings)
    # Create tables
    assert _engine is not None
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
