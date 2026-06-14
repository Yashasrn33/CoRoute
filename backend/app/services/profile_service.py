"""Profile: display name + the global default-preferences template, and applying
that template to a group's preferences on create/join."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Preference, User, UserDefaultPreference
from app.models.enums import PrefVisibility
from app.schemas.profile import DefaultPreferenceIn

_FIELDS = (
    "diet", "budget_min", "budget_max", "vibe_dislikes", "transportation",
    "hard_nos", "accessibility_needs", "notes",
)


async def update_name(session: AsyncSession, user_id: UUID, display_name: str) -> User:
    user = await session.get(User, user_id)
    if user is not None:
        user.display_name = display_name.strip()
        await session.flush()
    return user  # type: ignore[return-value]


async def get_default_preferences(
    session: AsyncSession, user_id: UUID
) -> UserDefaultPreference | None:
    return await session.get(UserDefaultPreference, user_id)


async def upsert_default_preferences(
    session: AsyncSession, user_id: UUID, data: DefaultPreferenceIn
) -> UserDefaultPreference:
    pref = await get_default_preferences(session, user_id)
    values = data.model_dump()
    if pref is None:
        pref = UserDefaultPreference(user_id=user_id, **values)
        session.add(pref)
    else:
        for f in _FIELDS:
            setattr(pref, f, values[f])
    await session.flush()
    return pref


async def apply_template_to_group(
    session: AsyncSession, group_id: UUID, user_id: UUID
) -> None:
    """If the user has a default template and no prefs yet for this group, seed the
    group's preferences from the template. No-op otherwise."""
    template = await get_default_preferences(session, user_id)
    if template is None:
        return
    existing = (
        await session.execute(
            select(Preference).where(
                Preference.group_id == group_id, Preference.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return
    session.add(Preference(
        group_id=group_id, user_id=user_id, visibility=PrefVisibility.private,
        **{f: getattr(template, f) for f in _FIELDS},
    ))
    await session.flush()
