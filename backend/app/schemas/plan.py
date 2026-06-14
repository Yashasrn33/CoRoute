"""Plan, attendance, and option schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import PlanStatus, PlanType, RsvpStatus


class PlanCreate(BaseModel):
    type: PlanType
    title: str
    scheduled_for: datetime | None = None
    location: str | None = None
    constraints: dict = Field(default_factory=dict)
    parent_plan_id: UUID | None = None


class PlanOut(BaseModel):
    id: UUID
    group_id: UUID
    created_by: UUID
    parent_plan_id: UUID | None
    type: PlanType
    status: PlanStatus
    title: str
    scheduled_for: datetime | None
    location: str | None
    constraints: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class RsvpIn(BaseModel):
    rsvp: RsvpStatus


class AttendeeOut(BaseModel):
    user_id: UUID
    display_name: str
    rsvp: RsvpStatus


class OptionOut(BaseModel):
    id: UUID
    plan_id: UUID
    title: str
    location: str | None
    description: str | None
    ai_reasoning: dict
    rank: int | None
    vote_total: int = 0
    my_score: int = 0

    model_config = {"from_attributes": True}


class VoteIn(BaseModel):
    option_id: UUID
    score: int = 1


class ExecuteIn(BaseModel):
    option_id: UUID


class ExecutionOut(BaseModel):
    id: UUID
    plan_id: UUID
    option_id: UUID
    kind: str
    status: str
    external_id: str | None

    model_config = {"from_attributes": True}


class PlanDetail(PlanOut):
    attendees: list[AttendeeOut]
    options: list[OptionOut]
