"""Auth request/response schemas."""

from uuid import UUID

from pydantic import BaseModel, EmailStr


class MagicLinkRequest(BaseModel):
    email: EmailStr
    display_name: str | None = None


class MagicLinkResponse(BaseModel):
    sent: bool
    # Dev-only convenience: with no email provider wired, return the token so the
    # flow is testable. Gated to non-production in the router.
    dev_magic_token: str | None = None


class VerifyRequest(BaseModel):
    token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID


class UserOut(BaseModel):
    id: UUID
    email: str
    display_name: str

    model_config = {"from_attributes": True}
