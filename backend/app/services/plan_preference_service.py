"""Per-plan preferences: a user reads/writes only their own (RLS-enforced)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PlanPreference
from app.schemas.plan_preference import PlanPreferenceIn

_EDITABLE = (
    "visibility", "diet", "budget_min", "budget_max", "vibe_dislikes",
    "transportation", "hard_nos", "accessibility_needs", "notes",
)


async def get_my_plan_preference(
    session: AsyncSession, plan_id: UUID, user_id: UUID
) -> PlanPreference | None:
    stmt = select(PlanPreference).where(
        PlanPreference.plan_id == plan_id, PlanPreference.user_id == user_id
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def upsert_my_plan_preference(
    session: AsyncSession, plan_id: UUID, user_id: UUID, data: PlanPreferenceIn
) -> PlanPreference:
    pref = await get_my_plan_preference(session, plan_id, user_id)
    values = data.model_dump()
    if pref is None:
        pref = PlanPreference(plan_id=plan_id, user_id=user_id, **values)
        session.add(pref)
    else:
        for field in _EDITABLE:
            setattr(pref, field, values[field])
    await session.flush()
    return pref
