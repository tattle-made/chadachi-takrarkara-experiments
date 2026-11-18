"""Takedown emails API: create drafts from the review screen, edit, list.

Any logged-in user can do everything here. Only drafts can be edited or
deleted; once an email is queued or sent it's read-only (409 otherwise).
Sending is done separately, by the background sender.
"""

import uuid

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUserDep, SessionDep
from app.api.routes.dmca.cases import get_case_or_404
from app.crud.dmca.takedown_email import (
    DraftError,
    create_drafts,
    delete_takedown_email,
    get_takedown_email,
    list_takedown_emails,
    to_public,
    update_takedown_email,
)
from app.models.dmca.enums import EmailStatus
from app.models.dmca.takedown_email import (
    DraftsCreate,
    DraftsResult,
    TakedownEmail,
    TakedownEmailPublic,
    TakedownEmailUpdate,
)

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
            status_code=409, detail=f"This email is {email.status.value}, not a draft"
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
