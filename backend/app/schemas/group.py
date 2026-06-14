"""Group + membership + invite schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import MemberRole


class GroupCreate(BaseModel):
    name: str


class GroupOut(BaseModel):
    id: UUID
    name: str
    created_by: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class MemberOut(BaseModel):
    user_id: UUID
    display_name: str
    role: MemberRole

    model_config = {"from_attributes": True}


class GroupDetail(GroupOut):
    members: list[MemberOut]


class InviteOut(BaseModel):
    invite_url: str
    token: str


class JoinRequest(BaseModel):
    token: str


class JoinResponse(BaseModel):
    group_id: UUID
    joined: bool
