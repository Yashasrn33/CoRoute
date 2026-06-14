"""Preferences: a user reads/writes ONLY their own (RLS-enforced). Readiness is
exposed via group_pref_status() which reveals existence, never content."""

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Preference, User
from app.schemas.preference import PreferenceIn

_EDITABLE = (
    "visibility",
    "diet",
    "budget_min",
    "budget_max",
    "vibe_dislikes",
    "transportation",
    "hard_nos",
    "accessibility_needs",
    "notes",
)


async def get_my_preference(
    session: AsyncSession, group_id: UUID, user_id: UUID
) -> Preference | None:
    stmt = select(Preference).where(
        Preference.group_id == group_id, Preference.user_id == user_id
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def upsert_my_preference(
    session: AsyncSession, group_id: UUID, user_id: UUID, data: PreferenceIn
) -> Preference:
    pref = await get_my_preference(session, group_id, user_id)
    values = data.model_dump()
    if pref is None:
        pref = Preference(group_id=group_id, user_id=user_id, **values)
        session.add(pref)
    else:
        for field in _EDITABLE:
            setattr(pref, field, values[field])
    await session.flush()
    return pref


async def preference_status(
    session: AsyncSession, group_id: UUID
) -> list[tuple[UUID, str, bool]]:
    """(user_id, display_name, has_prefs) for each member. Existence only."""
    rows = (
        await session.execute(
            text(
                "SELECT s.user_id, u.display_name, s.has_prefs "
                "FROM group_pref_status(:gid) s JOIN users u ON u.id = s.user_id "
                "ORDER BY u.display_name"
            ),
            {"gid": str(group_id)},
        )
    ).all()
    return [(r[0], r[1], r[2]) for r in rows]
