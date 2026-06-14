"""Profile schemas: display name + the global default-preferences template."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NameUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)


class DefaultPreferenceIn(BaseModel):
    diet: list[str] = Field(default_factory=list)
    budget_min: int | None = None
    budget_max: int | None = None
    vibe_dislikes: list[str] = Field(default_factory=list)
    transportation: list[str] = Field(default_factory=list)
    hard_nos: list[str] = Field(default_factory=list)
    accessibility_needs: list[str] = Field(default_factory=list)
    notes: str | None = None


class DefaultPreferenceOut(DefaultPreferenceIn):
    user_id: UUID
    updated_at: datetime

    model_config = {"from_attributes": True}
