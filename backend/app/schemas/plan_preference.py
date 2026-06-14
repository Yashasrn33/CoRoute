"""Per-plan preference schemas. Same shape as group preferences; these OVERRIDE
the user's general prefs per field for one plan (see synthesis merge)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import PrefVisibility


class PlanPreferenceIn(BaseModel):
    visibility: PrefVisibility = PrefVisibility.private
    diet: list[str] = Field(default_factory=list)
    budget_min: int | None = None
    budget_max: int | None = None
    vibe_dislikes: list[str] = Field(default_factory=list)
    transportation: list[str] = Field(default_factory=list)
    hard_nos: list[str] = Field(default_factory=list)
    accessibility_needs: list[str] = Field(default_factory=list)
    notes: str | None = None


class PlanPreferenceOut(PlanPreferenceIn):
    id: UUID
    plan_id: UUID
    user_id: UUID
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlanPreferenceSuggestion(PlanPreferenceIn):
    """AI-suggested plan prefs (not persisted). Includes a short rationale."""

    rationale: str | None = None
