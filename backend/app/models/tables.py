"""ORM table definitions. Mirrors docs/schema.sql.

Postgres enum types and RLS policies are created by the Alembic migration; here
we reference the enums with ``create_type=False`` so the ORM never tries to
re-create them.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import (
    ExecutionKind,
    MemberRole,
    PlanStatus,
    PlanType,
    PrefVisibility,
    RsvpStatus,
)


def _pk() -> Mapped[UUID]:
    return mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )


_TS = DateTime(timezone=True)


def _ts() -> Mapped[datetime]:
    return mapped_column(_TS, server_default=func.now(), nullable=False)


# enum column helpers (create_type=False — migration owns the type)
_role = ENUM(MemberRole, name="member_role", create_type=False)
_visibility = ENUM(PrefVisibility, name="pref_visibility", create_type=False)
_plan_type = ENUM(PlanType, name="plan_type", create_type=False)
_plan_status = ENUM(PlanStatus, name="plan_status", create_type=False)
_rsvp = ENUM(RsvpStatus, name="rsvp_status", create_type=False)
_exec_kind = ENUM(ExecutionKind, name="execution_kind", create_type=False)


class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = _pk()
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = _ts()


class Group(Base):
    __tablename__ = "groups"
    id: Mapped[UUID] = _pk()
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = _ts()


class GroupMember(Base):
    __tablename__ = "group_members"
    __table_args__ = (UniqueConstraint("group_id", "user_id"),)
    id: Mapped[UUID] = _pk()
    group_id: Mapped[UUID] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[MemberRole] = mapped_column(_role, nullable=False, default=MemberRole.member)
    joined_at: Mapped[datetime] = _ts()


class Preference(Base):
    __tablename__ = "preferences"
    __table_args__ = (UniqueConstraint("group_id", "user_id"),)
    id: Mapped[UUID] = _pk()
    group_id: Mapped[UUID] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    visibility: Mapped[PrefVisibility] = mapped_column(
        _visibility, nullable=False, default=PrefVisibility.private
    )
    diet: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    budget_min: Mapped[int | None] = mapped_column(Integer)
    budget_max: Mapped[int | None] = mapped_column(Integer)
    vibe_dislikes: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    transportation: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    hard_nos: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    accessibility_needs: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    notes: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = _ts()


class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[UUID] = _pk()
    group_id: Mapped[UUID] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    parent_plan_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("plans.id", ondelete="CASCADE")
    )
    type: Mapped[PlanType] = mapped_column(_plan_type, nullable=False)
    status: Mapped[PlanStatus] = mapped_column(
        _plan_status, nullable=False, default=PlanStatus.draft
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    scheduled_for: Mapped[datetime | None] = mapped_column(_TS)
    location: Mapped[str | None] = mapped_column(Text)
    constraints: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = _ts()


class PlanAttendee(Base):
    __tablename__ = "plan_attendees"
    __table_args__ = (UniqueConstraint("plan_id", "user_id"),)
    id: Mapped[UUID] = _pk()
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    rsvp: Mapped[RsvpStatus] = mapped_column(_rsvp, nullable=False, default=RsvpStatus.pending)
    responded_at: Mapped[datetime | None] = mapped_column(_TS)


class Option(Base):
    __tablename__ = "options"
    id: Mapped[UUID] = _pk()
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    ai_reasoning: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    external_ref: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    rank: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = _ts()


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("plan_id", "option_id", "user_id"),)
    id: Mapped[UUID] = _pk()
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    option_id: Mapped[UUID] = mapped_column(
        ForeignKey("options.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = _ts()


class Outcome(Base):
    __tablename__ = "outcomes"
    id: Mapped[UUID] = _pk()
    group_id: Mapped[UUID] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    option_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("options.id", ondelete="SET NULL")
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    happened_at: Mapped[datetime] = mapped_column(_TS, nullable=False)
    extra: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = _ts()


class Execution(Base):
    __tablename__ = "executions"
    id: Mapped[UUID] = _pk()
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    option_id: Mapped[UUID] = mapped_column(
        ForeignKey("options.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[ExecutionKind] = mapped_column(_exec_kind, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    external_id: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = _ts()
