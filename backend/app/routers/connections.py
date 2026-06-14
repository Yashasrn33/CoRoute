"""Connection (friends) routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user_id, get_rls_session
from app.schemas.connection import ConnectionRequest, ConnectionsOut
from app.services import connection_service
from app.services.connection_service import ConnectionError

router = APIRouter(prefix="/connections", tags=["connections"])


def _bad(exc: ConnectionError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("", response_model=ConnectionsOut)
async def list_connections(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> ConnectionsOut:
    return ConnectionsOut(**await connection_service.list_connections(session, user_id))


@router.post("/request", response_model=ConnectionsOut)
async def request(
    body: ConnectionRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> ConnectionsOut:
    try:
        await connection_service.request_connection(session, user_id, body.email)
    except ConnectionError as exc:
        raise _bad(exc) from exc
    return ConnectionsOut(**await connection_service.list_connections(session, user_id))


@router.post("/{connection_id}/accept", response_model=ConnectionsOut)
async def accept(
    connection_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> ConnectionsOut:
    try:
        await connection_service.respond(session, user_id, connection_id, accept=True)
    except ConnectionError as exc:
        raise _bad(exc) from exc
    return ConnectionsOut(**await connection_service.list_connections(session, user_id))


@router.delete("/{connection_id}", response_model=ConnectionsOut)
async def remove(
    connection_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> ConnectionsOut:
    """Decline an incoming request or remove an existing connection."""
    try:
        await connection_service.remove(session, user_id, connection_id)
    except ConnectionError as exc:
        raise _bad(exc) from exc
    return ConnectionsOut(**await connection_service.list_connections(session, user_id))
