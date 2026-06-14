"""Preference schemas. These represent ONLY the caller's own preferences — the
API never returns another member's preference content (see docs/privacy.md)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import PrefVisibility


class PreferenceIn(BaseModel):
    visibility: PrefVisibility = PrefVisibility.private
    diet: list[str] = Field(default_factory=list)
    budget_min: int | None = None
    budget_max: int | None = None
    vibe_dislikes: list[str] = Field(default_factory=list)
    transportation: list[str] = Field(default_factory=list)
    hard_nos: list[str] = Field(default_factory=list)
    accessibility_needs: list[str] = Field(default_factory=list)
    notes: str | None = None


class PreferenceOut(PreferenceIn):
    id: UUID
    group_id: UUID
    user_id: UUID
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemberPrefStatus(BaseModel):
    """Existence only — no preference content. Safe to show all members."""

    user_id: UUID
    display_name: str
    has_prefs: bool


class PrefStatusOut(BaseModel):
    group_id: UUID
    ready: int
    total: int
    members: list[MemberPrefStatus]
