"""Attachments API: upload a profile's documents, list them, download one.

Any logged-in user can do everything here. Files go to storage (Google Drive),
so uploading and downloading need Google connected (409 otherwise).
Documents can't be deleted yet.
"""

import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Form, HTTPException, Response, UploadFile

from app.api.deps import CurrentUserDep, SessionDep
from app.api.routes.dmca.profiles import get_profile_or_404
from app.crud.dmca.attachment import (
    create_attachment,
    get_attachment,
    list_attachments,
)
from app.models.dmca.attachment import MAX_ATTACHMENT_BYTES, AttachmentPublic
from app.models.dmca.enums import AttachmentKind
from app.services.google_auth import GoogleNotConnected
from app.services.storage import Storage, get_storage

router = APIRouter(prefix="/dmca", tags=["dmca"])


def storage_or_409(session: SessionDep) -> Storage:
    """The configured storage, or stop with a 409 if Google isn't connected."""
    try:
        return get_storage(session=session)
    except GoogleNotConnected as err:
        raise HTTPException(
            status_code=409, detail=f"{err}. An admin can connect it in Config."
        ) from None


@router.post("/profiles/{profile_id}/attachments", response_model=AttachmentPublic)
def upload_attachment(
    session: SessionDep,
    current_user: CurrentUserDep,
    profile_id: uuid.UUID,
    kind: Annotated[AttachmentKind, Form()],
    file: UploadFile,
) -> AttachmentPublic:
    """Upload a document to a profile (multipart form: kind + file).

    400 for an empty file, 413 over 20 MB, 409 if Google isn't connected.
    """
    get_profile_or_404(session, profile_id)
    assert current_user.id is not None

    # read one byte past the limit, so a too-big file is caught without
    # reading all of it
    data = file.file.read(MAX_ATTACHMENT_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="The file is empty")
    if len(data) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=413, detail="The file is over 20 MB")

    file_name = file.filename or "document"
    mime_type = file.content_type or "application/octet-stream"
    storage = storage_or_409(session)
    storage_key = storage.save(file_name, data, mime_type)

    attachment = create_attachment(
        session=session,
        profile_id=profile_id,
        kind=kind,
        file_name=file_name,
        mime_type=mime_type,
        size=len(data),
        storage_key=storage_key,
        uploaded_by=current_user.id,
    )
    return AttachmentPublic.model_validate(attachment)


@router.get("/profiles/{profile_id}/attachments", response_model=list[AttachmentPublic])
def get_profile_attachments(
    session: SessionDep, _: CurrentUserDep, profile_id: uuid.UUID
) -> list[AttachmentPublic]:
    """A profile's documents, newest first."""
    get_profile_or_404(session, profile_id)
    return [
        AttachmentPublic.model_validate(a)
        for a in list_attachments(session=session, profile_id=profile_id)
    ]


@router.get("/attachments/{attachment_id}/file")
def download_attachment(
    session: SessionDep, _: CurrentUserDep, attachment_id: uuid.UUID
) -> Response:
    """The file itself, as a download."""
    attachment = get_attachment(session=session, attachment_id=attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Document not found")
    stored = storage_or_409(session).get(attachment.storage_key)
    # filename*= lets non-English names through
    disposition = f"attachment; filename*=UTF-8''{quote(attachment.file_name)}"
    return Response(
        content=stored.data,
        media_type=attachment.mime_type,
        headers={"Content-Disposition": disposition},
    )
