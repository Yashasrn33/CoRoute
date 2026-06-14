"""FastAPI dependencies: current user + the RLS-scoped DB session.

The RLS session is the app-layer half of the privacy model (the DB-layer half is
the policies in the migration). Every authenticated request runs inside a single
transaction that begins with ``SET LOCAL app.current_user_id = <uid>`` via
``set_config(..., is_local => true)``. Because it's transaction-scoped, the
identity can never leak onto the next request that reuses a pooled connection.
"""

from collections.abc import AsyncIterator
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import decode_token

_bearer = HTTPBearer(auto_error=True)


async def get_current_user_id(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> UUID:
    try:
        claims = decode_token(creds.credentials, expected_type="access")
        return UUID(claims["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


async def get_rls_session(
    user_id: UUID = Depends(get_current_user_id),
) -> AsyncIterator[AsyncSession]:
    """Yield a session bound to one transaction with the RLS identity set."""
    async with SessionLocal() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.current_user_id', :uid, true)"),
                {"uid": str(user_id)},
            )
            yield session


async def get_plain_session() -> AsyncIterator[AsyncSession]:
    """Session without an RLS identity — for pre-auth endpoints only (users has no RLS)."""
    async with SessionLocal() as session:
        yield session
