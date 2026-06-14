"""Enumerations shared by ORM models and Pydantic schemas.

The string values MUST match the Postgres enum labels in docs/schema.sql / the
Alembic migration.
"""

from enum import Enum


class MemberRole(str, Enum):
    owner = "owner"
    member = "member"


class PrefVisibility(str, Enum):
    private = "private"
    group = "group"


class PlanType(str, Enum):
    dinner = "dinner"
    watch_party = "watch_party"
    trip = "trip"
    activity = "activity"
    other = "other"


class PlanStatus(str, Enum):
    draft = "draft"
    collecting = "collecting"
    options_ready = "options_ready"
    voting = "voting"
    decided = "decided"
    executed = "executed"


class RsvpStatus(str, Enum):
    yes = "yes"
    maybe = "maybe"
    no = "no"
    pending = "pending"


class ExecutionKind(str, Enum):
    calendar = "calendar"
    booking = "booking"
    payment_split = "payment_split"
