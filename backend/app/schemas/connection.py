"""Connection (friends) schemas."""

from uuid import UUID

from pydantic import BaseModel, EmailStr


class ConnectionRequest(BaseModel):
    email: EmailStr


class ConnectionPerson(BaseModel):
    """The other user in a connection, plus the connection's id/direction."""

    connection_id: UUID
    user_id: UUID
    display_name: str
    email: str


class ConnectionsOut(BaseModel):
    friends: list[ConnectionPerson]
    incoming: list[ConnectionPerson]  # pending requests awaiting MY acceptance
    outgoing: list[ConnectionPerson]  # pending requests I sent


class AddFriendToGroup(BaseModel):
    user_id: UUID
