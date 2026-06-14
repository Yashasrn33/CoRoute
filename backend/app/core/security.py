"""JWT helpers for magic-link auth.

Two token kinds, both HS256:
  * ``magic`` — short-lived, emailed as a login link (sub = email).
  * ``access`` — the session token returned after verifying a magic token
    (sub = user id).
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from app.core.config import get_settings

settings = get_settings()
ALGORITHM = "HS256"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_magic_token(email: str) -> str:
    payload = {
        "sub": email,
        "type": "magic",
        "exp": _now() + timedelta(minutes=settings.magic_link_ttl_minutes),
        "iat": _now(),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def create_access_token(user_id: UUID) -> str:
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": _now() + timedelta(minutes=settings.jwt_expires_minutes),
        "iat": _now(),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def create_invite_token(group_id: UUID) -> str:
    payload = {
        "sub": str(group_id),
        "type": "invite",
        "exp": _now() + timedelta(days=14),
        "iat": _now(),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str, *, expected_type: str) -> dict:
    """Decode and validate a token, asserting its ``type`` claim.

    Raises ``jwt.InvalidTokenError`` (or subclass) on any problem.
    """
    claims = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    if claims.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"expected {expected_type} token")
    return claims
