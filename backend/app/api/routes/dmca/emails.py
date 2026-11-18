"""Takedown emails API: create drafts from the review screen, edit, list.

Any logged-in user can do everything here. Only drafts can be edited or
deleted; once an email is queued or sent it's read-only (409 otherwise).
POST /emails/send hands drafts to the background queue, which sends them one at
a time; /retry sends a failed (or stuck) one again.
"""

import uuid

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUserDep, SessionDep
from app.api.routes.dmca.cases import get_case_or_404
from app.crud.dmca.google_connection import get_connection
from app.crud.dmca.takedown_email import (
    DraftError,
    can_retry,
    create_drafts,
    delete_takedown_email,
    get_takedown_email,
    list_by_ids,
    list_takedown_emails,
    mark_queued,
    to_public,
    update_takedown_email,
)
from app.models.dmca.enums import EmailStatus, GoogleConnectionStatus
from app.models.dmca.takedown_email import (
    DraftsCreate,
    DraftsResult,
    EmailsSend,
    TakedownEmail,
    TakedownEmailPublic,
    TakedownEmailUpdate,
)

from app.services.queue import enqueue_sends

router = APIRouter(prefix="/dmca", tags=["dmca"])


def get_email_or_404(session: SessionDep, email_id: uuid.UUID) -> TakedownEmail:
    """Load the email from the URL, or stop with a 404."""
    email = get_takedown_email(session=session, email_id=email_id)
    if email is None:
        raise HTTPException(status_code=404, detail="Email not found")
    return email


def ensure_draft(email: TakedownEmail) -> None:
    """Stop with a 409 unless the email is still a draft."""
    if email.status != EmailStatus.draft:
        raise HTTPException(
            status_code=409,
            detail=(
                f"The email to {email.recipient_name} is already "
                f"{email.status.value}. Refresh and try again."
            ),
        )


@router.post("/cases/{case_id}/drafts", response_model=DraftsResult)
def create_case_drafts(
    session: SessionDep,
    current_user: CurrentUserDep,
    case_id: uuid.UUID,
    body: DraftsCreate,
) -> DraftsResult:
    """Create draft emails from the review screen (also used by Escalate).

    Body: {"items": [{"domain": "example-site.com", "recipient_id": "...",
                      "email_type": "dmca", "relation": "cdn",
                      "add_to_email_id": null}, ...]}
    Without add_to_email_id: one new draft per recipient + email type, covering
    its domains' links. Each starts with the address picked from the
    recipient's emails, a subject built from its domains, and the default legal
    grounds.
    With add_to_email_id: the links go into that existing draft instead, and its
    body is reset to the template.

    Links marked removed are left out. Returns {"created": [...], "updated": [...]}.
    400 if a recipient doesn't exist or lacks the chosen type, the draft to add
    to can't be used, or there are no links to send.
    """
    case = get_case_or_404(session, case_id)
    assert current_user.id is not None
    try:
        created, updated = create_drafts(
            session=session, case=case, items=body.items, created_by=current_user.id
        )
    except DraftError as err:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(err)) from None
    return DraftsResult(
        created=[to_public(d) for d in created],
        updated=[to_public(d) for d in updated],
    )


@router.get("/emails", response_model=list[TakedownEmailPublic])
def get_emails(
    session: SessionDep,
    _: CurrentUserDep,
    case_id: uuid.UUID | None = None,
    status: EmailStatus | None = None,
) -> list[TakedownEmailPublic]:
    """List emails, newest first. ?case_id= for one case, ?status= e.g. draft."""
    emails = list_takedown_emails(session=session, case_id=case_id, status=status)
    return [to_public(e) for e in emails]


@router.get("/emails/{email_id}", response_model=TakedownEmailPublic)
def get_one_email(
    session: SessionDep, _: CurrentUserDep, email_id: uuid.UUID
) -> TakedownEmailPublic:
    """Get one email, with the body as it will be (or was) sent."""
    return to_public(get_email_or_404(session, email_id))


@router.patch("/emails/{email_id}", response_model=TakedownEmailPublic)
def update_one_email(
    session: SessionDep,
    _: CurrentUserDep,
    email_id: uuid.UUID,
    email_in: TakedownEmailUpdate,
) -> TakedownEmailPublic:
    """Edit a draft: To address, subject, body, links, legal grounds, documents.

    {"custom_body": null} throws away body edits and goes back to the template.
    link_ids / legal_ground_ids / attachment_ids replace the whole list.
    """
    email = get_email_or_404(session, email_id)
    ensure_draft(email)
    try:
        updated = update_takedown_email(
            session=session, db_email=email, email_in=email_in
        )
    except DraftError as err:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(err)) from None
    return to_public(updated)


@router.delete("/emails/{email_id}")
def delete_one_email(
    session: SessionDep, _: CurrentUserDep, email_id: uuid.UUID
) -> dict[str, str]:
    """Throw away a draft. Queued or sent emails can't be deleted."""
    email = get_email_or_404(session, email_id)
    ensure_draft(email)
    delete_takedown_email(session=session, db_email=email)
    return {"message": "Draft deleted"}


# --- sending ---


def ensure_google_connected(session: SessionDep) -> None:
    """Stop with a 409 if Google isn't connected, before anything is queued."""
    connection = get_connection(session=session)
    if connection is None or connection.status != GoogleConnectionStatus.connected:
        raise HTTPException(
            status_code=409,
            detail="Google isn't connected. An admin can connect it in Config.",
        )


def queue_or_503(session: SessionDep, emails: list[TakedownEmail]) -> None:
    """Mark the emails queued and add their send jobs. If the queue can't take
    them, put them back the way they were and stop with a 503."""
    before = [(e, e.status, e.last_error, e.updated_at) for e in emails]
    mark_queued(session=session, emails=emails)
    try:
        enqueue_sends([email.id for email in emails])
    except Exception:
        for email, status, last_error, updated_at in before:
            email.status = status
            email.last_error = last_error
            email.updated_at = updated_at
            session.add(email)
        session.commit()
        raise HTTPException(
            status_code=503, detail="Couldn't start sending. Try again in a bit."
        ) from None


@router.post("/emails/send", response_model=list[TakedownEmailPublic])
def send_emails(
    session: SessionDep, _: CurrentUserDep, body: EmailsSend
) -> list[TakedownEmailPublic]:
    """Send drafts: {"email_ids": [...]}. All or nothing.

    Each becomes "queued", and the background queue sends them one by one
    (queued -> sending -> sent or failed). 404 if an id doesn't exist, 409 if
    one isn't a draft or Google isn't connected, 400 if one has no To address.
    """
    ids = set(body.email_ids)
    emails = list_by_ids(session=session, email_ids=list(ids))
    if len(emails) != len(ids):
        raise HTTPException(status_code=404, detail="Some emails don't exist")
    for email in emails:
        ensure_draft(email)
        if not email.to_address:
            raise HTTPException(
                status_code=400,
                detail=f"The email to {email.recipient_name} has no To address",
            )
    ensure_google_connected(session)
    queue_or_503(session, emails)
    return [to_public(e) for e in emails]


@router.post("/emails/{email_id}/retry", response_model=TakedownEmailPublic)
def retry_email(
    session: SessionDep, _: CurrentUserDep, email_id: uuid.UUID
) -> TakedownEmailPublic:
    """Send a failed email again (or one stuck in "sending" for 10+ minutes).

    It gets a fresh set of tries. 409 if it can't be retried (can_retry is false)
    or Google isn't connected.
    """
    email = get_email_or_404(session, email_id)
    if not can_retry(email):
        raise HTTPException(
            status_code=409, detail=f"This email is {email.status.value}; can't retry"
        )
    ensure_google_connected(session)
    queue_or_503(session, [email])
    return to_public(email)
