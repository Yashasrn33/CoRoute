"""Friends/connections: request, accept, decline, list, and add a friend to a group.

RLS is the real boundary (a user only sees rows where they're requester/addressee;
only the addressee accepts). These functions add friendly errors + the reverse-
request collapse (if B already requested A, A 'requesting' B just accepts it).
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Connection, GroupMember, User
from app.models.enums import ConnectionStatus, MemberRole


class ConnectionError(Exception):
    """Raised for invalid connection operations (mapped to 400 in the router)."""


async def request_connection(session: AsyncSession, me: UUID, email: str) -> Connection:
    email = email.lower().strip()
    other = (
        await session.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if other is None:
        raise ConnectionError("No CoRoute user with that email")
    if other.id == me:
        raise ConnectionError("You can't connect with yourself")

    # Any existing connection in either direction?
    existing = (
        await session.execute(
            select(Connection).where(
                or_(
                    (Connection.requester_id == me) & (Connection.addressee_id == other.id),
                    (Connection.requester_id == other.id) & (Connection.addressee_id == me),
                )
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        if existing.status == ConnectionStatus.accepted:
            raise ConnectionError("You're already connected")
        # A pending request the OTHER person sent me -> accept it (collapse reverse).
        if existing.addressee_id == me:
            existing.status = ConnectionStatus.accepted
            existing.responded_at = datetime.now(timezone.utc)
            await session.flush()
            return existing
        raise ConnectionError("Request already pending")

    conn = Connection(requester_id=me, addressee_id=other.id)
    session.add(conn)
    await session.flush()
    return conn


async def respond(session: AsyncSession, me: UUID, connection_id: UUID, accept: bool) -> None:
    conn = await session.get(Connection, connection_id)
    # RLS already restricts visibility; double-check the addressee.
    if conn is None or conn.addressee_id != me or conn.status != ConnectionStatus.pending:
        raise ConnectionError("No pending request to respond to")
    if accept:
        conn.status = ConnectionStatus.accepted
        conn.responded_at = datetime.now(timezone.utc)
    else:
        await session.delete(conn)
    await session.flush()


async def remove(session: AsyncSession, me: UUID, connection_id: UUID) -> None:
    conn = await session.get(Connection, connection_id)
    if conn is None or me not in (conn.requester_id, conn.addressee_id):
        raise ConnectionError("Connection not found")
    await session.delete(conn)
    await session.flush()


async def list_connections(session: AsyncSession, me: UUID) -> dict[str, list]:
    rows = (
        await session.execute(
            select(Connection).where(
                or_(Connection.requester_id == me, Connection.addressee_id == me)
            )
        )
    ).scalars().all()
    # Resolve the "other" user for each.
    other_ids = {c.requester_id if c.addressee_id == me else c.addressee_id for c in rows}
    users = {
        u.id: u
        for u in (
            await session.execute(select(User).where(User.id.in_(other_ids)))
        ).scalars().all()
    }
    friends, incoming, outgoing = [], [], []
    for c in rows:
        other_id = c.requester_id if c.addressee_id == me else c.addressee_id
        u = users.get(other_id)
        if u is None:
            continue
        person = {
            "connection_id": c.id, "user_id": u.id,
            "display_name": u.display_name, "email": u.email,
        }
        if c.status == ConnectionStatus.accepted:
            friends.append(person)
        elif c.addressee_id == me:
            incoming.append(person)
        else:
            outgoing.append(person)
    return {"friends": friends, "incoming": incoming, "outgoing": outgoing}


async def add_friend_to_group(
    session: AsyncSession, me: UUID, group_id: UUID, friend_id: UUID
) -> bool:
    """Add a confirmed friend to a group I'm in. RLS enforces both conditions via
    the gm_insert_friend policy; returns False if already a member."""
    existing = (
        await session.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id, GroupMember.user_id == friend_id
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return False
    session.add(GroupMember(group_id=group_id, user_id=friend_id, role=MemberRole.member))
    await session.flush()
    return True
