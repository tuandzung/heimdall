from __future__ import annotations

import pytest
from fastapi_users import InvalidPasswordException

from heimdall.config import AppConfig
from heimdall.db import User
from heimdall.users import UserManager


class MockUserDB:
    """Mock user database for testing"""

    pass


@pytest.fixture
def user_manager():
    """Fixture to create a UserManager instance for testing"""
    settings = AppConfig()
    return UserManager(MockUserDB(), settings)


@pytest.fixture
def user():
    """Fixture to create a test user"""
    return User(email="test@example.com")


class TestUserManagerDomainRestriction:
    """Test domain and email restriction functionality in UserManager"""

    @pytest.mark.asyncio
    async def test_validate_password_no_restrictions(self, user_manager, user):
        """Test that any email is allowed when no restrictions are set"""
        # No restrictions configured
        user_manager.settings.auth.allowed_emails = []
        user_manager.settings.auth.allowed_domains = []

        # Should not raise any exception
        await user_manager.validate_password("testpassword123", user)

    @pytest.mark.asyncio
    async def test_validate_password_domain_restriction_allowed(self, user_manager):
        """Test that emails from allowed domains are accepted"""
        user_manager.settings.auth.allowed_domains = ["example.com"]
        user_manager.settings.auth.allowed_emails = []

        user = User(email="user@example.com")

        # Should not raise any exception
        await user_manager.validate_password("testpassword123", user)

    @pytest.mark.asyncio
    async def test_validate_password_domain_restriction_rejected(self, user_manager):
        """Test that emails from non-allowed domains are rejected"""
        user_manager.settings.auth.allowed_domains = ["example.com"]
        user_manager.settings.auth.allowed_emails = []

        user = User(email="user@other.com")

        # Should raise InvalidPasswordException
        with pytest.raises(InvalidPasswordException) as exc_info:
            await user_manager.validate_password("testpassword123", user)

        assert "Email address is not allowed for registration" in getattr(exc_info.value, "reason", "")

    @pytest.mark.asyncio
    async def test_validate_password_email_restriction_allowed(self, user_manager):
        """Test that specific allowed emails are accepted"""
        user_manager.settings.auth.allowed_emails = ["admin@company.com"]
        user_manager.settings.auth.allowed_domains = []

        user = User(email="admin@company.com")

        # Should not raise any exception
        await user_manager.validate_password("testpassword123", user)

    @pytest.mark.asyncio
    async def test_validate_password_email_restriction_rejected(self, user_manager):
        """Test that non-allowed emails are rejected"""
        user_manager.settings.auth.allowed_emails = ["admin@company.com"]
        user_manager.settings.auth.allowed_domains = []

        user = User(email="user@company.com")

        # Should raise InvalidPasswordException
        with pytest.raises(InvalidPasswordException) as exc_info:
            await user_manager.validate_password("testpassword123", user)

        assert "Email address is not allowed for registration" in getattr(exc_info.value, "reason", "")

    @pytest.mark.asyncio
    async def test_validate_password_both_restrictions_email_takes_precedence(self, user_manager):
        """Test that specific email takes precedence over domain restrictions"""
        user_manager.settings.auth.allowed_emails = ["special@anydomain.com"]
        user_manager.settings.auth.allowed_domains = ["example.com"]

        # Email is in allowed_emails but domain is not in allowed_domains
        user = User(email="special@anydomain.com")

        # Should not raise any exception (email takes precedence)
        await user_manager.validate_password("testpassword123", user)

    @pytest.mark.asyncio
    async def test_validate_password_both_restrictions_domain_fallback(self, user_manager):
        """Test that domain restriction works when email is not explicitly allowed"""
        user_manager.settings.auth.allowed_emails = ["admin@company.com"]
        user_manager.settings.auth.allowed_domains = ["example.com"]

        # Email is not in allowed_emails but domain is in allowed_domains
        user = User(email="user@example.com")

        # Should not raise any exception
        await user_manager.validate_password("testpassword123", user)

    @pytest.mark.asyncio
    async def test_validate_password_both_restrictions_rejected(self, user_manager):
        """Test rejection when neither email nor domain is allowed"""
        user_manager.settings.auth.allowed_emails = ["admin@company.com"]
        user_manager.settings.auth.allowed_domains = ["example.com"]

        # Email is not in allowed_emails and domain is not in allowed_domains
        user = User(email="user@other.com")

        # Should raise InvalidPasswordException
        with pytest.raises(InvalidPasswordException) as exc_info:
            await user_manager.validate_password("testpassword123", user)

        assert "Email address is not allowed for registration" in getattr(exc_info.value, "reason", "")

    @pytest.mark.asyncio
    async def test_validate_password_invalid_email_format(self, user_manager):
        """Test behavior with invalid email format"""
        user_manager.settings.auth.allowed_domains = ["example.com"]
        user_manager.settings.auth.allowed_emails = []

        # Invalid email format
        user = User(email="invalid-email")

        # Should raise InvalidPasswordException (domain extraction fails)
        with pytest.raises(InvalidPasswordException) as exc_info:
            await user_manager.validate_password("testpassword123", user)

        assert "Email address is not allowed for registration" in getattr(exc_info.value, "reason", "")

    @pytest.mark.asyncio
    async def test_validate_password_empty_domain_list(self, user_manager):
        """Test behavior with empty domain list but populated email list"""
        user_manager.settings.auth.allowed_emails = ["admin@company.com"]
        user_manager.settings.auth.allowed_domains = []

        # Email not in allowed_emails
        user = User(email="user@example.com")

        # Should raise InvalidPasswordException
        with pytest.raises(InvalidPasswordException) as exc_info:
            await user_manager.validate_password("testpassword123", user)

        assert "Email address is not allowed for registration" in getattr(exc_info.value, "reason", "")

    @pytest.mark.asyncio
    async def test_validate_password_empty_email_list(self, user_manager):
        """Test behavior with empty email list but populated domain list"""
        user_manager.settings.auth.allowed_emails = []
        user_manager.settings.auth.allowed_domains = ["example.com"]

        # Domain not in allowed_domains
        user = User(email="user@other.com")

        # Should raise InvalidPasswordException
        with pytest.raises(InvalidPasswordException) as exc_info:
            await user_manager.validate_password("testpassword123", user)

        assert "Email address is not allowed for registration" in getattr(exc_info.value, "reason", "")

    @pytest.mark.asyncio
    async def test_validate_password_password_length_validation(self, user_manager, user):
        """Test that password length validation still works alongside domain restrictions"""
        user_manager.settings.auth.allowed_emails = []
        user_manager.settings.auth.allowed_domains = []

        # Short password should still be rejected
        with pytest.raises(InvalidPasswordException) as exc_info:
            await user_manager.validate_password("short", user)

        assert "Password should be at least 8 characters" in getattr(exc_info.value, "reason", "")

    @pytest.mark.asyncio
    async def test_validate_password_user_create_object(self, user_manager):
        """Test that the validation works with UserCreate objects as well"""
        user_manager.settings.auth.allowed_domains = ["example.com"]
        user_manager.settings.auth.allowed_emails = []

        # Create a mock UserCreate-like object
        class MockUserCreate:
            def __init__(self, email):
                self.email = email

        # Should work with UserCreate-like objects
        user_create = MockUserCreate("user@example.com")
        await user_manager.validate_password("testpassword123", user_create)

        # Should reject non-allowed domains
        user_create_rejected = MockUserCreate("user@other.com")
        with pytest.raises(InvalidPasswordException):
            await user_manager.validate_password("testpassword123", user_create_rejected)
