"""Profile routes: update display name + manage the default-preferences template."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user_id, get_rls_session
from app.models import User
from app.schemas.auth import UserOut
from app.schemas.profile import DefaultPreferenceIn, DefaultPreferenceOut, NameUpdate
from app.services import profile_service

router = APIRouter(prefix="/me", tags=["profile"])


@router.patch("", response_model=UserOut)
async def update_name(
    body: NameUpdate,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> User:
    return await profile_service.update_name(session, user_id, body.display_name)


@router.get("/default-preferences", response_model=DefaultPreferenceOut | None)
async def get_defaults(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> DefaultPreferenceOut | None:
    pref = await profile_service.get_default_preferences(session, user_id)
    return DefaultPreferenceOut.model_validate(pref) if pref else None


@router.put("/default-preferences", response_model=DefaultPreferenceOut)
async def put_defaults(
    body: DefaultPreferenceIn,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> DefaultPreferenceOut:
    pref = await profile_service.upsert_default_preferences(session, user_id, body)
    return DefaultPreferenceOut.model_validate(pref)
