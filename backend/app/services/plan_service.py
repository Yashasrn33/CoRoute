"""Plan lifecycle + attendance. All on the RLS-scoped session (member-only)."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Execution, Option, Outcome, Plan, PlanAttendee, User, Vote
from app.models.enums import ExecutionKind, PlanStatus, RsvpStatus
from app.schemas.plan import PlanCreate


async def create_plan(session: AsyncSession, group_id: UUID, creator: UUID, data: PlanCreate) -> Plan:
    plan = Plan(
        group_id=group_id,
        created_by=creator,
        parent_plan_id=data.parent_plan_id,
        type=data.type,
        title=data.title,
        scheduled_for=data.scheduled_for,
        location=data.location,
        constraints=data.constraints,
    )
    session.add(plan)
    await session.flush()
    # Creator is attending by default.
    session.add(PlanAttendee(plan_id=plan.id, user_id=creator, rsvp=RsvpStatus.yes,
                             responded_at=datetime.now(timezone.utc)))
    await session.flush()
    return plan


async def list_plans(session: AsyncSession, group_id: UUID) -> list[Plan]:
    stmt = select(Plan).where(Plan.group_id == group_id).order_by(Plan.created_at.desc())
    return list((await session.execute(stmt)).scalars().all())


async def get_plan(session: AsyncSession, plan_id: UUID) -> Plan | None:
    return await session.get(Plan, plan_id)


async def set_rsvp(session: AsyncSession, plan_id: UUID, user_id: UUID, rsvp: RsvpStatus) -> None:
    existing = (
        await session.execute(
            select(PlanAttendee).where(
                PlanAttendee.plan_id == plan_id, PlanAttendee.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        session.add(PlanAttendee(plan_id=plan_id, user_id=user_id, rsvp=rsvp,
                                 responded_at=datetime.now(timezone.utc)))
    else:
        existing.rsvp = rsvp
        existing.responded_at = datetime.now(timezone.utc)
    await session.flush()


async def list_attendees(session: AsyncSession, plan_id: UUID) -> list[tuple[PlanAttendee, User]]:
    stmt = (
        select(PlanAttendee, User)
        .join(User, User.id == PlanAttendee.user_id)
        .where(PlanAttendee.plan_id == plan_id)
        .order_by(User.display_name)
    )
    return [tuple(r) for r in (await session.execute(stmt)).all()]


async def list_options(session: AsyncSession, plan_id: UUID) -> list[Option]:
    stmt = select(Option).where(Option.plan_id == plan_id).order_by(Option.rank)
    return list((await session.execute(stmt)).scalars().all())


async def vote_tallies(session: AsyncSession, plan_id: UUID, user_id: UUID) -> dict[UUID, tuple[int, int]]:
    """option_id -> (total_score, my_score)."""
    totals = (
        await session.execute(
            select(Vote.option_id, func.coalesce(func.sum(Vote.score), 0))
            .where(Vote.plan_id == plan_id)
            .group_by(Vote.option_id)
        )
    ).all()
    mine = (
        await session.execute(
            select(Vote.option_id, Vote.score).where(
                Vote.plan_id == plan_id, Vote.user_id == user_id
            )
        )
    ).all()
    my_map = {oid: s for oid, s in mine}
    return {oid: (int(total), int(my_map.get(oid, 0))) for oid, total in totals}


async def cast_vote(
    session: AsyncSession, plan_id: UUID, option_id: UUID, user_id: UUID, score: int
) -> None:
    existing = (
        await session.execute(
            select(Vote).where(
                Vote.plan_id == plan_id, Vote.option_id == option_id, Vote.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        session.add(Vote(plan_id=plan_id, option_id=option_id, user_id=user_id, score=score))
    else:
        existing.score = score
    if (await get_plan(session, plan_id)).status == PlanStatus.options_ready:  # type: ignore[union-attr]
        plan = await get_plan(session, plan_id)
        plan.status = PlanStatus.voting  # type: ignore[union-attr]
    await session.flush()


async def execute_winner(
    session: AsyncSession, plan: Plan, option_id: UUID
) -> Execution:
    """Calendar-execute stub: create an execution + write the outcome (group memory),
    and mark the plan executed. Closes the loop."""
    option = await session.get(Option, option_id)
    execution = Execution(
        plan_id=plan.id,
        option_id=option_id,
        kind=ExecutionKind.calendar,
        status="created",
        external_id=f"cal_stub_{plan.id.hex[:8]}",
        payload={"note": "calendar invite stub — wire Google Calendar in Step 8"},
    )
    session.add(execution)
    session.add(
        Outcome(
            group_id=plan.group_id,
            plan_id=plan.id,
            option_id=option_id,
            summary=f"{option.title}" if option else plan.title,
            happened_at=plan.scheduled_for or datetime.now(timezone.utc),
            extra={"source": "executed_plan"},
        )
    )
    plan.status = PlanStatus.executed
    await session.flush()
    return execution
