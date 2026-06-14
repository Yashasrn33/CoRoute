"""Group lifecycle: create, list, detail, invite, join.

All DB access here runs on the RLS-scoped session, so the policies are the real
authorization boundary — these functions add app-layer checks on top (defense in
depth) and produce friendly errors.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Group, GroupMember, User
from app.models.enums import MemberRole


async def create_group(session: AsyncSession, name: str, owner_id: UUID) -> Group:
    group = Group(name=name, created_by=owner_id)
    session.add(group)
    await session.flush()  # get group.id
    session.add(GroupMember(group_id=group.id, user_id=owner_id, role=MemberRole.owner))
    await session.flush()
    return group


async def list_my_groups(session: AsyncSession, user_id: UUID) -> list[Group]:
    # RLS already restricts to the caller's groups; the join keeps it explicit.
    stmt = (
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(GroupMember.user_id == user_id)
        .order_by(Group.created_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_group(session: AsyncSession, group_id: UUID) -> Group | None:
    # RLS returns None for non-members.
    return await session.get(Group, group_id)


async def list_members(session: AsyncSession, group_id: UUID) -> list[tuple[GroupMember, User]]:
    stmt = (
        select(GroupMember, User)
        .join(User, User.id == GroupMember.user_id)
        .where(GroupMember.group_id == group_id)
        .order_by(GroupMember.joined_at)
    )
    return [tuple(row) for row in (await session.execute(stmt)).all()]


async def join_group(session: AsyncSession, group_id: UUID, user_id: UUID) -> bool:
    """Add the caller to a group (idempotent). Returns True if newly added.

    Authorized by possession of a valid invite token (decoded by the caller).
    RLS permits a user to insert only their own membership row.
    """
    existing = (
        await session.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id, GroupMember.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return False
    session.add(GroupMember(group_id=group_id, user_id=user_id, role=MemberRole.member))
    await session.flush()
    return True
