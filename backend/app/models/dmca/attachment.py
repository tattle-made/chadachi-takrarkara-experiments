"""Attachments: documents on a profile (cyber crime report, ID, age proof, ...).

A file is uploaded once to the profile and can then be attached to any of its
takedown emails. The file itself lives in storage (Google Drive); this table
holds its details and storage_key, the id to fetch it with.
"""

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel

from app.models.dmca.enums import AttachmentKind

# Gmail allows 25 MB per email, counted after attachments are encoded for
# email (about a third bigger): 18 MB of files is about 24 MB once encoded
MAX_ATTACHMENT_MB = 18
MAX_ATTACHMENT_BYTES = MAX_ATTACHMENT_MB * 1024 * 1024


class Attachment(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    profile_id: uuid.UUID = Field(
        foreign_key="profile.id", ondelete="CASCADE", index=True
    )
    kind: AttachmentKind
    file_name: str = Field(max_length=255)
    mime_type: str = Field(max_length=255)
    size: int  # bytes
    # the file's id in storage (the Drive file id)
    storage_key: str = Field(max_length=255)
    uploaded_by: int = Field(foreign_key="user.id")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )


class AttachmentPublic(SQLModel):
    id: uuid.UUID
    profile_id: uuid.UUID
    kind: AttachmentKind
    file_name: str
    mime_type: str
    size: int
    created_at: datetime
