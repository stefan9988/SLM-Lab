"""Google OAuth + JWT authentication module."""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Header, HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from pydantic import BaseModel

from BE.config import settings
from BE.logger import setup_logger

logger = setup_logger(__name__)


class UserInfo(BaseModel):
    """Authenticated user information carried in the JWT."""

    id: str = ""
    email: str
    name: str
    picture: str = ""
    google_sub: str = ""


def verify_google_token(token: str) -> UserInfo:
    """Verify a Google OAuth2 ID token and return user info.

    Raises HTTPException 401 on any verification failure.
    """
    try:
        id_info = google_id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            audience=settings.GOOGLE_CLIENT_ID,
        )
        return UserInfo(
            email=id_info["email"],
            name=id_info.get("name", ""),
            picture=id_info.get("picture", ""),
            google_sub=id_info["sub"],
        )
    except (ValueError, KeyError) as exc:
        logger.warning("Google token verification failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid Google token") from exc


def create_access_token(user: UserInfo) -> str:
    """Create an HS256 JWT containing the user's info."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.email,
        "name": user.name,
        "picture": user.picture,
        "user_id": user.id,
        "iat": now,
        "exp": now + timedelta(hours=settings.JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def get_current_user(authorization: str = Header(...)) -> UserInfo:
    """FastAPI dependency – extract and validate the Bearer JWT.

    Returns the authenticated ``UserInfo`` or raises 401.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[len("Bearer ") :]
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=["HS256"],
        )
        return UserInfo(
            id=payload.get("user_id", ""),
            email=payload["sub"],
            name=payload.get("name", ""),
            picture=payload.get("picture", ""),
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token has expired") from exc
    except (jwt.InvalidTokenError, KeyError) as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
