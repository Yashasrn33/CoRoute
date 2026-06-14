"""Auth flow: magic-link issuance + verification.

Magic tokens are self-contained JWTs (no token table needed). On verify we
get-or-create the user keyed by the email in the token, then mint an access token.
"""

from uuid import UUID

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, create_magic_token, decode_token
from app.models import User


async def get_or_create_user(
    session: AsyncSession, email: str, display_name: str | None = None
) -> User:
    email = email.lower().strip()
    user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        user = User(email=email, display_name=display_name or email.split("@")[0])
        session.add(user)
        await session.flush()
    return user


async def request_magic_link(
    session: AsyncSession, email: str, display_name: str | None
) -> str:
    """Ensure the user exists and return a magic token (caller emails the link)."""
    await get_or_create_user(session, email, display_name)
    await session.commit()
    return create_magic_token(email.lower().strip())


async def verify_magic_token(session: AsyncSession, token: str) -> tuple[str, UUID]:
    """Validate a magic token; return (access_token, user_id). Raises on bad token."""
    claims = decode_token(token, expected_type="magic")
    email = claims["sub"]
    user = await get_or_create_user(session, email)
    await session.commit()
    return create_access_token(user.id), user.id


__all__ = ["get_or_create_user", "request_magic_link", "verify_magic_token", "jwt"]
