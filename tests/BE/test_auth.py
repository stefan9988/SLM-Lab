"""Tests for BE.auth module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException

from BE.auth import UserInfo, create_access_token, get_current_user, verify_google_token
from BE.config import settings


class TestVerifyGoogleToken:
    @patch("BE.auth.google_id_token.verify_oauth2_token")
    def test_valid_token_returns_user_info(self, mock_verify):
        mock_verify.return_value = {
            "email": "user@example.com",
            "name": "Test User",
            "picture": "https://example.com/photo.jpg",
        }
        user = verify_google_token("valid-token")
        assert user.email == "user@example.com"
        assert user.name == "Test User"
        assert user.picture == "https://example.com/photo.jpg"

    @patch("BE.auth.google_id_token.verify_oauth2_token")
    def test_invalid_token_raises_401(self, mock_verify):
        mock_verify.side_effect = ValueError("Invalid token")
        with pytest.raises(HTTPException) as exc_info:
            verify_google_token("bad-token")
        assert exc_info.value.status_code == 401

    @patch("BE.auth.google_id_token.verify_oauth2_token")
    def test_missing_email_raises_401(self, mock_verify):
        mock_verify.return_value = {"name": "No Email"}
        with pytest.raises(HTTPException) as exc_info:
            verify_google_token("token-no-email")
        assert exc_info.value.status_code == 401


class TestCreateAccessToken:
    def test_jwt_contains_user_info(self):
        user = UserInfo(email="a@b.com", name="Alice", picture="pic.jpg")
        token = create_access_token(user)
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        assert payload["sub"] == "a@b.com"
        assert payload["name"] == "Alice"
        assert payload["picture"] == "pic.jpg"

    def test_jwt_has_expiration(self):
        user = UserInfo(email="a@b.com", name="Alice", picture="")
        token = create_access_token(user)
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        delta = exp - iat
        assert delta == timedelta(hours=settings.JWT_EXPIRATION_HOURS)


class TestGetCurrentUser:
    def test_valid_bearer_token(self):
        user = UserInfo(email="x@y.com", name="X", picture="")
        token = create_access_token(user)
        result = get_current_user(f"Bearer {token}")
        assert result.email == "x@y.com"
        assert result.name == "X"

    def test_missing_bearer_prefix_raises_401(self):
        user = UserInfo(email="x@y.com", name="X", picture="")
        token = create_access_token(user)
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token)
        assert exc_info.value.status_code == 401
        assert "Invalid authorization header" in exc_info.value.detail

    def test_expired_token_raises_401(self):
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "x@y.com",
            "name": "X",
            "picture": "",
            "iat": now - timedelta(hours=48),
            "exp": now - timedelta(hours=1),
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(f"Bearer {token}")
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail

    def test_wrong_secret_raises_401(self):
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "x@y.com",
            "name": "X",
            "picture": "",
            "iat": now,
            "exp": now + timedelta(hours=1),
        }
        token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(f"Bearer {token}")
        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail
