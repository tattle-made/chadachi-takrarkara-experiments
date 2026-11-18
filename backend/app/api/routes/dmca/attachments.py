"""Attachments API: upload a profile's documents, list them, download one.

Any logged-in user can do everything here. Files go to storage (Google Drive),
so uploading and downloading need Google connected (409 otherwise). If Drive
itself fails, the route returns 502 with Google's message.
Documents can't be deleted yet.
"""

import uuid
from collections.abc import Generator
from contextlib import contextmanager
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
from app.models.dmca.attachment import (
    MAX_ATTACHMENT_BYTES,
    MAX_ATTACHMENT_MB,
    AttachmentPublic,
)
from app.models.dmca.enums import AttachmentKind
from app.services.google_auth import GoogleNotConnected
from app.services.google_errors import GOOGLE_ERRORS, describe
from app.services.storage import get_storage

router = APIRouter(prefix="/dmca", tags=["dmca"])


@contextmanager
def drive_errors(action: str) -> Generator[None]:
    """Turn Google's errors inside the with-block into messages for the UI:
    409 if Google isn't connected, 502 (Google failed) with Google's message
    otherwise. Other errors are our bugs and stay a 500."""
    try:
        yield
    except GoogleNotConnected as err:
        raise HTTPException(
            status_code=409, detail=f"{err}. An admin can connect it in Config."
        ) from None
    except GOOGLE_ERRORS as err:
        raise HTTPException(
            status_code=502, detail=f"{action}: {describe(err)}"
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

    400 for an empty file, 413 over the size limit, 409 if Google isn't
    connected, 502 if Drive fails.
    """
    get_profile_or_404(session, profile_id)
    assert current_user.id is not None

    # read one byte past the limit, so a too-big file is caught without
    # reading all of it
    data = file.file.read(MAX_ATTACHMENT_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="The file is empty")
    if len(data) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(
            status_code=413, detail=f"The file is over {MAX_ATTACHMENT_MB} MB"
        )

    file_name = file.filename or "document"
    mime_type = file.content_type or "application/octet-stream"
    with drive_errors("Couldn't upload the file to Drive"):
        storage_key = get_storage(session=session).save(file_name, data, mime_type)

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
    with drive_errors("Couldn't download the file from Drive"):
        stored = get_storage(session=session).get(attachment.storage_key)
    # filename*= lets non-English names through
    disposition = f"attachment; filename*=UTF-8''{quote(attachment.file_name)}"
    return Response(
        content=stored.data,
        media_type=attachment.mime_type,
        headers={"Content-Disposition": disposition},
    )
