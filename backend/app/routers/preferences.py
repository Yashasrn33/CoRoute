"""Preference routes — scoped to one group. A member reads/writes only their own
preferences; readiness shows existence (never content) for all members."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user_id, get_rls_session
from app.schemas.preference import (
    MemberPrefStatus,
    PreferenceIn,
    PreferenceOut,
    PrefStatusOut,
)
from app.services import group_service, preference_service

router = APIRouter(prefix="/groups/{group_id}/preferences", tags=["preferences"])


async def _require_member(session: AsyncSession, group_id: UUID) -> None:
    # RLS returns None for non-members; surface a clean 404.
    if await group_service.get_group(session, group_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")


@router.get("/me", response_model=PreferenceOut | None)
async def get_my_preferences(
    group_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> PreferenceOut | None:
    await _require_member(session, group_id)
    pref = await preference_service.get_my_preference(session, group_id, user_id)
    return PreferenceOut.model_validate(pref) if pref else None


@router.put("/me", response_model=PreferenceOut)
async def put_my_preferences(
    group_id: UUID,
    body: PreferenceIn,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> PreferenceOut:
    await _require_member(session, group_id)
    pref = await preference_service.upsert_my_preference(session, group_id, user_id, body)
    return PreferenceOut.model_validate(pref)


@router.get("/status", response_model=PrefStatusOut)
async def get_status(
    group_id: UUID,
    _user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> PrefStatusOut:
    await _require_member(session, group_id)
    rows = await preference_service.preference_status(session, group_id)
    members = [
        MemberPrefStatus(user_id=uid, display_name=name, has_prefs=has)
        for uid, name, has in rows
    ]
    return PrefStatusOut(
        group_id=group_id,
        ready=sum(1 for m in members if m.has_prefs),
        total=len(members),
        members=members,
    )
