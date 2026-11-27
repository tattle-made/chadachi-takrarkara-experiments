"""DB functions for the Config section: recipients, their emails and domain links.

These only talk to the DB. HTTP concerns stay in the routes:
- get_* return None when nothing is found; the route turns that into a 404.
- A duplicate hits a unique constraint and raises IntegrityError; the route
  rolls back and returns a 409.
"""

import uuid
from datetime import datetime, timezone

from sqlmodel import Session, col, select

from app.models.dmca.recipient import (
    Domain,
    DomainLinkCreate,
    DomainRecipient,
    DomainResolved,
    Recipient,
    RecipientCreate,
    RecipientEmail,
    RecipientEmailCreate,
    RecipientUpdate,
)

# --- recipients ---


def create_recipient(*, session: Session, recipient_in: RecipientCreate) -> Recipient:
    # turn the input schema into a table row (runs validators, fills id/timestamps)
    recipient = Recipient.model_validate(recipient_in)
    session.add(recipient)
    session.commit()
    # reload from the DB so the returned object has everything the DB saved
    session.refresh(recipient)
    return recipient


def list_recipients(
    *, session: Session, skip: int = 0, limit: int = 100
) -> list[Recipient]:
    # skip/limit = pagination: skip the first `skip` rows, return at most `limit`
    return list(session.exec(select(Recipient).offset(skip).limit(limit)))


def get_recipient(*, session: Session, recipient_id: uuid.UUID) -> Recipient | None:
    return session.get(Recipient, recipient_id)


def update_recipient(
    *, session: Session, db_recipient: Recipient, recipient_in: RecipientUpdate
) -> Recipient:
    # exclude_unset: only the fields the client actually sent, so a PATCH with
    # just {"notes": ...} doesn't wipe the name
    update_data = recipient_in.model_dump(exclude_unset=True)
    db_recipient.sqlmodel_update(update_data)
    db_recipient.updated_at = datetime.now(timezone.utc)
    session.add(db_recipient)
    session.commit()
    session.refresh(db_recipient)
    return db_recipient


def delete_recipient(*, session: Session, db_recipient: Recipient) -> None:
    # cascade_delete on the relationships removes its emails and domain links too
    session.delete(db_recipient)
    session.commit()


# --- recipient emails ---


def get_email(*, session: Session, email_id: uuid.UUID) -> RecipientEmail | None:
    return session.get(RecipientEmail, email_id)


def add_email(
    *, session: Session, recipient_id: uuid.UUID, email_in: RecipientEmailCreate
) -> RecipientEmail:
    # model_validate (not RecipientEmail(...)) so the lowercase validator runs.
    # recipient_id comes from the URL, not the body, so it's passed via update=
    email = RecipientEmail.model_validate(
        email_in, update={"recipient_id": recipient_id}
    )
    session.add(email)
    session.commit()
    session.refresh(email)
    return email


def delete_email(*, session: Session, db_email: RecipientEmail) -> None:
    session.delete(db_email)
    session.commit()


# --- domain recipients ---


def normalise_domain(name: str) -> str:
    # same rule as the DomainBase validator. Needed for searches, because the
    # validator only runs when a row is created, not when we query
    return name.strip().lower()


def get_domain_by_name(*, session: Session, name: str) -> Domain | None:
    name = normalise_domain(name)
    return session.exec(select(Domain).where(Domain.domain == name)).first()


def get_or_create_domain(*, session: Session, name: str) -> Domain:
    # no commit here on purpose: add_domain_recipient commits the domain and the
    # link together, so we never save a domain without its link
    db_domain = get_domain_by_name(session=session, name=name)
    if db_domain is None:
        db_domain = Domain.model_validate({"domain": name})
        session.add(db_domain)
    return db_domain


def add_domain_recipient(
    *, session: Session, recipient_id: uuid.UUID, link_in: DomainLinkCreate
) -> DomainRecipient:
    # a new domain already has its id (default_factory), so we can use it
    # before anything is committed
    db_domain = get_or_create_domain(session=session, name=link_in.domain)
    domain_recipient = DomainRecipient(
        domain_id=db_domain.id, recipient_id=recipient_id, relation=link_in.relation
    )
    session.add(domain_recipient)
    # saves the (maybe new) domain and the link in one go. Same domain + recipient
    # + relation twice -> IntegrityError from the unique constraint
    session.commit()
    session.refresh(domain_recipient)
    return domain_recipient


def get_domain_recipient(
    *, session: Session, domain_recipient_id: uuid.UUID
) -> DomainRecipient | None:
    return session.get(DomainRecipient, domain_recipient_id)


def delete_domain_recipient(
    *, session: Session, db_domain_recipient: DomainRecipient
) -> None:
    # only this row goes; the Domain stays for other recipients
    session.delete(db_domain_recipient)
    session.commit()


# --- resolve ---


def resolve_domains(*, session: Session, names: list[str]) -> list[DomainResolved]:
    """For each domain name, the recipients linked to it (empty if it's unknown)."""
    # normalise and drop blanks/duplicates, keeping the input order.
    # dict.fromkeys keeps the first occurrence of each key, in order
    cleaned = list(dict.fromkeys(normalise_domain(n) for n in names if n.strip()))
    if not cleaned:
        return []

    # one query for all known domains, then look each name up in a dict
    rows = session.exec(select(Domain).where(col(Domain.domain).in_(cleaned))).all()
    by_name = {row.domain: row for row in rows}

    resolved = []
    for name in cleaned:
        row = by_name.get(name)
        if row is None:
            # not in Config yet: the UI shows it as "no recipient"
            resolved.append(DomainResolved(domain=name))
        else:
            # follows row.recipient_links -> each link's recipient (lazy-loaded)
            resolved.append(DomainResolved.model_validate(row))
    return resolved
