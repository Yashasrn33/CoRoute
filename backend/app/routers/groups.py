"""Group routes: create, list, detail, invite link, join."""

from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_current_user_id, get_rls_session
from app.core.security import create_invite_token, decode_token
from app.schemas.connection import AddFriendToGroup
from app.schemas.group import (
    GroupCreate,
    GroupDetail,
    GroupOut,
    InviteOut,
    JoinRequest,
    JoinResponse,
    MemberOut,
)
from app.services import connection_service, group_service

router = APIRouter(prefix="/groups", tags=["groups"])
settings = get_settings()


@router.post("", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
async def create_group(
    body: GroupCreate,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> GroupOut:
    group = await group_service.create_group(session, body.name, user_id)
    return GroupOut.model_validate(group)


@router.get("", response_model=list[GroupOut])
async def list_groups(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> list[GroupOut]:
    groups = await group_service.list_my_groups(session, user_id)
    return [GroupOut.model_validate(g) for g in groups]


@router.get("/{group_id}", response_model=GroupDetail)
async def group_detail(
    group_id: UUID,
    _user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> GroupDetail:
    group = await group_service.get_group(session, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    members = await group_service.list_members(session, group_id)
    return GroupDetail(
        **GroupOut.model_validate(group).model_dump(),
        members=[
            MemberOut(user_id=gm.user_id, display_name=user.display_name, role=gm.role)
            for gm, user in members
        ],
    )


@router.post("/{group_id}/invite", response_model=InviteOut)
async def create_invite(
    group_id: UUID,
    _user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> InviteOut:
    # Only a member can mint an invite (RLS returns None otherwise).
    group = await group_service.get_group(session, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    token = create_invite_token(group_id)
    return InviteOut(invite_url=f"{settings.app_base_url}/join?token={token}", token=token)


@router.post("/{group_id}/friends", response_model=GroupDetail)
async def add_friend(
    group_id: UUID,
    body: AddFriendToGroup,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> GroupDetail:
    # Must be a member to add anyone (RLS also enforces this + friendship).
    if await group_service.get_group(session, group_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    try:
        await connection_service.add_friend_to_group(session, user_id, group_id, body.user_id)
    except Exception as exc:  # RLS rejects non-friends
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only add a confirmed friend to the group",
        ) from exc
    return await group_detail(group_id, user_id, session)


@router.post("/join", response_model=JoinResponse)
async def join(
    body: JoinRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> JoinResponse:
    try:
        claims = decode_token(body.token, expected_type="invite")
        group_id = UUID(claims["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired invite"
        ) from exc
    joined = await group_service.join_group(session, group_id, user_id)
    return JoinResponse(group_id=group_id, joined=joined)
