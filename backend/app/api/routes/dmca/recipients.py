"""Config API: recipients, their emails and domain links.

Reads are open to any logged-in user (the review screen needs them); writes are
admin-only. All paths start with /api/v1/dmca.
"""

import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import IntegrityError

from app.api.deps import AdminDep, CurrentUserDep, SessionDep
from app.crud.dmca.recipient import (
    add_domain_recipient,
    add_email,
    create_recipient,
    delete_domain_recipient,
    delete_email,
    delete_recipient,
    get_domain_recipient,
    get_email,
    get_recipient,
    list_recipients,
    resolve_domains,
    update_recipient,
)
from app.models.dmca.recipient import (
    DomainLinkCreate,
    DomainLinkPublic,
    DomainResolved,
    Recipient,
    RecipientCreate,
    RecipientEmailCreate,
    RecipientEmailPublic,
    RecipientPublic,
    RecipientsPublic,
    RecipientUpdate,
)

router = APIRouter(prefix="/dmca", tags=["dmca"])


def get_recipient_or_404(session: SessionDep, recipient_id: uuid.UUID) -> Recipient:
    """Load the recipient from the URL, or stop the request with a 404."""
    recipient = get_recipient(session=session, recipient_id=recipient_id)
    if recipient is None:
        raise HTTPException(status_code=404, detail="Recipient not found")
    return recipient


# --- recipients ---


# args that aren't in the path (limit, skip) become query params: ?limit=10&skip=0
@router.get("/recipients", response_model=RecipientsPublic)
def get_recipients(
    session: SessionDep, _: CurrentUserDep, limit: int = 100, skip: int = 0
) -> RecipientsPublic:
    """List recipients (one page), each with its emails and domain links."""
    recipients_list = list_recipients(session=session, skip=skip, limit=limit)
    return RecipientsPublic(data=recipients_list, count=len(recipients_list))


@router.post("/recipients", response_model=RecipientPublic)
def create_new_recipient(
    session: SessionDep, _: AdminDep, recipient_in: RecipientCreate
) -> RecipientPublic:
    """Admin: create a recipient (name + notes). Emails and domains are added after."""
    new_recipient = create_recipient(session=session, recipient_in=recipient_in)
    # table row -> response schema (also fills emails and domain_links)
    return RecipientPublic.model_validate(new_recipient)


# {recipient_id} in the path matches the recipient_id arg; FastAPI turns the text
# into a UUID and returns a 422 if it isn't one
@router.get("/recipients/{recipient_id}", response_model=RecipientPublic)
def get_one_recipient(
    session: SessionDep, _: CurrentUserDep, recipient_id: uuid.UUID
) -> RecipientPublic:
    """Get one recipient with its emails and domain links."""
    recipient = get_recipient_or_404(session, recipient_id)
    return RecipientPublic.model_validate(recipient)


@router.patch("/recipients/{recipient_id}", response_model=RecipientPublic)
def update_one_recipient(
    session: SessionDep,
    _: AdminDep,
    recipient_id: uuid.UUID,
    recipient_in: RecipientUpdate,
) -> RecipientPublic:
    """Admin: change the name and/or notes. Fields left out of the body stay as is."""
    recipient = get_recipient_or_404(session, recipient_id)
    updated = update_recipient(
        session=session, db_recipient=recipient, recipient_in=recipient_in
    )
    return RecipientPublic.model_validate(updated)


@router.delete("/recipients/{recipient_id}")
def delete_one_recipient(
    session: SessionDep, _: AdminDep, recipient_id: uuid.UUID
) -> dict[str, str]:
    """Admin: delete a recipient. Its emails and domain links are deleted with it."""
    recipient = get_recipient_or_404(session, recipient_id)
    delete_recipient(session=session, db_recipient=recipient)
    return {"message": "Recipient deleted"}


# --- recipient emails ---


@router.post("/recipients/{recipient_id}/emails", response_model=RecipientEmailPublic)
def add_recipient_email(
    session: SessionDep,
    _: AdminDep,
    recipient_id: uuid.UUID,
    email_in: RecipientEmailCreate,
) -> RecipientEmailPublic:
    """Admin: add an address (with its type, e.g. abuse) to a recipient.

    409 if the same address + type is already saved, under any recipient.
    """
    get_recipient_or_404(session, recipient_id)
    try:
        email = add_email(session=session, recipient_id=recipient_id, email_in=email_in)
    except IntegrityError:
        # a failed commit leaves the session unusable until it's rolled back
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="This address is already added for this email type",
        )
    return RecipientEmailPublic.model_validate(email)


@router.delete("/recipients/{recipient_id}/emails/{email_id}")
def delete_recipient_email(
    session: SessionDep, _: AdminDep, recipient_id: uuid.UUID, email_id: uuid.UUID
) -> dict[str, str]:
    """Admin: remove one address from a recipient."""
    email = get_email(session=session, email_id=email_id)
    # also check it belongs to this recipient, so a wrong URL can't delete
    # another recipient's email
    if email is None or email.recipient_id != recipient_id:
        raise HTTPException(status_code=404, detail="Email not found")
    delete_email(session=session, db_email=email)
    return {"message": "Email deleted"}


# --- domain links ---


@router.post("/recipients/{recipient_id}/domains", response_model=DomainLinkPublic)
def add_recipient_domain(
    session: SessionDep,
    _: AdminDep,
    recipient_id: uuid.UUID,
    link_in: DomainLinkCreate,
) -> DomainLinkPublic:
    """Admin: link a domain to this recipient with a relation.

    Body: {"domain": "example-site.com", "relation": "cdn"}. The domain is created
    if it's new. 409 if this recipient already has this relation for the domain.
    """
    get_recipient_or_404(session, recipient_id)
    try:
        link = add_domain_recipient(
            session=session, recipient_id=recipient_id, link_in=link_in
        )
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="This recipient already has this relation for this domain",
        )
    return DomainLinkPublic.model_validate(link)


@router.delete("/recipients/{recipient_id}/domains/{domain_recipient_id}")
def delete_recipient_domain(
    session: SessionDep,
    _: AdminDep,
    recipient_id: uuid.UUID,
    domain_recipient_id: uuid.UUID,
) -> dict[str, str]:
    """Admin: remove one domain link. The domain itself stays (others may use it)."""
    link = get_domain_recipient(
        session=session, domain_recipient_id=domain_recipient_id
    )
    if link is None or link.recipient_id != recipient_id:
        raise HTTPException(status_code=404, detail="Domain link not found")
    delete_domain_recipient(session=session, db_domain_recipient=link)
    return {"message": "Domain link deleted"}


# --- resolve (review screen) ---


@router.get("/domains/resolve", response_model=list[DomainResolved])
def resolve(
    session: SessionDep, _: CurrentUserDep, domains: str
) -> list[DomainResolved]:
    """Who do we email for these sites? Used to pre-fill the review screen.

    The counsellor pastes links; the frontend pulls out their domains and calls
    GET /dmca/domains/resolve?domains=example-site.com,unknown.com

    Returns one entry per domain with the recipients linked to it:
        [
          {"domain": "example-site.com", "recipient_links": [
              {"relation": "cdn", "recipient": {"id": ..., "name": "Cloudflare",
                                                "email_types": ["dmca", "abuse"]}},
              ...]},
          {"domain": "unknown.com", "recipient_links": []}   <- not in Config yet
        ]

    email_types feeds the email type dropdown: the types this recipient has an
    address for.
    """
    # `domains` arrives as one string, "a.com,b.com"; split it into a list
    return resolve_domains(session=session, names=domains.split(","))
