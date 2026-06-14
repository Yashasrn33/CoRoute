"""Auth routes: request a magic link, verify it, and inspect the current user."""

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_current_user_id, get_plain_session, get_rls_session
from app.models import User
from app.schemas.auth import (
    MagicLinkRequest,
    MagicLinkResponse,
    TokenResponse,
    UserOut,
    VerifyRequest,
)
from app.services import auth_service
from app.core.logging import get_logger

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
log = get_logger("coroute.auth")


@router.post("/magic-link", response_model=MagicLinkResponse)
async def magic_link(
    body: MagicLinkRequest,
    session: AsyncSession = Depends(get_plain_session),
) -> MagicLinkResponse:
    token = await auth_service.request_magic_link(session, body.email, body.display_name)
    link = f"{settings.app_base_url}/auth/verify?token={token}"
    log.info("magic link issued for %s -> %s", body.email, link)
    # In dev, return the token so the flow is testable without an email provider.
    return MagicLinkResponse(
        sent=True,
        dev_magic_token=None if settings.is_production else token,
    )


@router.post("/verify", response_model=TokenResponse)
async def verify(
    body: VerifyRequest,
    session: AsyncSession = Depends(get_plain_session),
) -> TokenResponse:
    try:
        access_token, user_id = await auth_service.verify_magic_token(session, body.token)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired link"
        ) from exc
    return TokenResponse(access_token=access_token, user_id=user_id)


@router.get("/me", response_model=UserOut)
async def me(
    user_id=Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
