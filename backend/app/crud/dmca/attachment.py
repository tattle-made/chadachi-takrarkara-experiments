"""DB functions for attachments (profile documents). The file itself is saved
to storage by the route; these only handle the rows."""

import uuid

from sqlmodel import Session, col, select

from app.models.dmca.attachment import Attachment
from app.models.dmca.enums import AttachmentKind


def create_attachment(
    *,
    session: Session,
    profile_id: uuid.UUID,
    kind: AttachmentKind,
    file_name: str,
    mime_type: str,
    size: int,
    storage_key: str,
    uploaded_by: int,
) -> Attachment:
    """Save the row for a file already in storage (storage_key is its id there)."""
    attachment = Attachment(
        profile_id=profile_id,
        kind=kind,
        file_name=file_name,
        mime_type=mime_type,
        size=size,
        storage_key=storage_key,
        uploaded_by=uploaded_by,
    )
    session.add(attachment)
    session.commit()
    session.refresh(attachment)
    return attachment


def get_attachment(*, session: Session, attachment_id: uuid.UUID) -> Attachment | None:
    """One document by id, or None."""
    return session.get(Attachment, attachment_id)


def list_attachments(*, session: Session, profile_id: uuid.UUID) -> list[Attachment]:
    """A profile's documents, newest first."""
    query = (
        select(Attachment)
        .where(Attachment.profile_id == profile_id)
        .order_by(col(Attachment.created_at).desc())
    )
    return list(session.exec(query))
