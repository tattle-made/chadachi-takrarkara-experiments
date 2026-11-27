"""The shared Google account the app sends emails and stores files with.

There's at most one row: an admin connects the account once, and connecting
again replaces it. The refresh token is stored encrypted (app/core/crypto.py).
"""

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel

from app.models.dmca.enums import GoogleConnectionStatus


class GoogleConnection(SQLModel, table=True):
    __tablename__ = "dmca_google_connection"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    account_email: str = Field(max_length=255)
    refresh_token_encrypted: str
    # space-separated, as Google returns them
    scopes: str
    status: GoogleConnectionStatus = GoogleConnectionStatus.connected
    # why it broke, e.g. "invalid_grant: Token has been expired or revoked."
    last_error: str | None = None
    connected_by: int | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL"
    )
    connected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )


# --- API schemas ---


class GoogleConnectUrl(SQLModel):
    url: str


class GoogleStatus(SQLModel):
    # true when emails can be sent
    connected: bool
    # None if Google was never connected
    status: GoogleConnectionStatus | None = None
    account_email: str | None = None
    connected_at: datetime | None = None
    last_error: str | None = None
