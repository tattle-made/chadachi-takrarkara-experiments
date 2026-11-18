"""DB functions for takedown emails: creating drafts, editing them, reading them.

Problems the counsellor can fix (unknown recipient, a link from another case, ...)
raise DraftError; the routes turn it into a 400.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlmodel import Session, col, select

from app.models.dmca.case import Case, CaseLink, CaseLinkPublic
from app.models.dmca.enums import DomainRelation, EmailStatus, EmailType
from app.models.dmca.legal_ground import LegalGround, LegalGroundPublic
from app.models.dmca.recipient import Recipient
from app.models.dmca.takedown_email import (
    DraftItem,
    TakedownEmail,
    TakedownEmailPublic,
    TakedownEmailUpdate,
)
from app.services.template import (
    AddressInput,
    GroundInput,
    LinkInput,
    build_subject,
    pick_address,
    render_body,
    unique_domains,
)


class DraftError(Exception):
    """Something in the request the counsellor needs to fix (becomes a 400)."""


def _sorted_links(links: list[CaseLink]) -> list[CaseLink]:
    # the order they were added to the case, so the email lists them that way
    return sorted(links, key=lambda link: (link.created_at, link.url))


def _sorted_grounds(grounds: list[LegalGround]) -> list[LegalGround]:
    return sorted(grounds, key=lambda g: g.created_at)


def default_legal_grounds(*, session: Session, is_minor: bool) -> list[LegalGround]:
    """The grounds ticked on a new draft: active, default_selected, and the
    minor-only ones only for a minor case."""
    query = select(LegalGround).where(
        col(LegalGround.active).is_(True),
        col(LegalGround.default_selected).is_(True),
    )
    if not is_minor:
        query = query.where(col(LegalGround.minor_only).is_(False))
    return _sorted_grounds(list(session.exec(query)))


# --- creating drafts ---


@dataclass
class _Group:
    """Review-screen rows that become one email: same recipient and address type.

    e.g. site-a.com -> Cloudflare and site-b.com -> Cloudflare are one group.
    """

    recipient: Recipient
    email_type: EmailType | None
    to_address: str | None
    # the draft to add the links to, or None to make a new one
    existing: TakedownEmail | None
    domains: set[str] = field(default_factory=set)
    relations: set[DomainRelation | None] = field(default_factory=set)


def _existing_draft(*, session: Session, case: Case, item: DraftItem) -> TakedownEmail:
    """Load the draft a row wants its links added to (its add_to_email_id).

    DraftError unless it's in this case, still a draft, and for the same recipient.
    """
    email = session.get(TakedownEmail, item.add_to_email_id)
    if email is None or email.case_id != case.id:
        raise DraftError("The draft to add to isn't in this case")
    if email.status != EmailStatus.draft:
        raise DraftError("The email to add to isn't a draft any more")
    if email.recipient_id != item.recipient_id:
        raise DraftError("The draft to add to is for a different recipient")
    return email


def _subject_for(links: list[CaseLink], is_minor: bool) -> str:
    return build_subject(
        unique_domains([LinkInput(link.url, link.domain) for link in links]), is_minor
    )


def _one_relation(relations: set[DomainRelation | None]) -> DomainRelation | None:
    # one relation for the whole email if all rows agree, else unknown
    return next(iter(relations)) if len(relations) == 1 else None


def create_drafts(
    *, session: Session, case: Case, items: list[DraftItem], created_by: int
) -> tuple[list[TakedownEmail], list[TakedownEmail]]:
    """Turn the review screen's rows into draft emails. Returns (created, updated).

    Each row says "send this domain's links to this recipient". Rows for the same
    recipient + address type become one new email covering all their domains.
    A row with add_to_email_id adds its links to that existing draft instead; an
    edited body there is reset so the new links show up in it.

    Links marked removed are left out. Links already emailed are not: sending
    one again is allowed (the review screen warns about it). Escalate uses the
    same call with the next recipient.
    """
    pending = [link for link in _sorted_links(case.links) if link.removed_at is None]

    # load every recipient the rows mention, in one query
    recipient_ids = {item.recipient_id for item in items}
    recipients = {
        r.id: r
        for r in session.exec(
            select(Recipient).where(col(Recipient.id).in_(recipient_ids))
        )
    }

    # group the rows. Key: (recipient, address type, existing draft or None)
    groups: dict[tuple[uuid.UUID, EmailType | None, uuid.UUID | None], _Group] = {}
    for item in items:
        recipient = recipients.get(item.recipient_id)
        if recipient is None:
            raise DraftError(f"Recipient {item.recipient_id} not found")

        if item.add_to_email_id is not None:
            # the draft already has its address; email_type is ignored
            existing = _existing_draft(session=session, case=case, item=item)
            email_type, address = existing.email_type, existing.to_address
        else:
            existing = None
            addresses = [
                AddressInput(address=e.address, email_type=e.email_type)
                for e in sorted(recipient.emails, key=lambda e: e.created_at)
            ]
            try:
                picked = pick_address(
                    addresses, is_minor=case.is_minor, chosen_type=item.email_type
                )
            except ValueError:
                raise DraftError(
                    f"{recipient.name} has no {item.email_type} address"
                ) from None
            email_type, address = picked if picked else (None, None)

        key = (recipient.id, email_type, item.add_to_email_id)
        group = groups.setdefault(key, _Group(recipient, email_type, address, existing))
        group.domains.add(item.domain.strip().lower())
        group.relations.add(item.relation)

    grounds = default_legal_grounds(session=session, is_minor=case.is_minor)

    created: list[TakedownEmail] = []
    updated: list[TakedownEmail] = []
    for group in groups.values():
        # links the draft being added to already has aren't added twice
        skip = {link.id for link in group.existing.links} if group.existing else set()
        links = [
            link
            for link in pending
            if link.domain in group.domains and link.id not in skip
        ]
        if not links:
            continue

        if group.existing is None:
            draft = TakedownEmail(
                case_id=case.id,
                recipient_id=group.recipient.id,
                recipient_name=group.recipient.name,
                relation=_one_relation(group.relations),
                email_type=group.email_type,
                to_address=group.to_address,
                subject=_subject_for(links, case.is_minor),
                created_by=created_by,
                links=links,
                legal_grounds=grounds,
            )
            session.add(draft)
            created.append(draft)
        else:
            draft = group.existing
            old_links = list(draft.links)
            all_links = _sorted_links([*old_links, *links])
            # update the subject too, unless the counsellor changed it by hand
            if draft.subject == _subject_for(old_links, case.is_minor):
                draft.subject = _subject_for(all_links, case.is_minor)
            draft.links = all_links
            draft.relation = _one_relation({draft.relation, *group.relations})
            # back to the generated body, so the new links appear in it
            draft.custom_body = None
            draft.updated_at = datetime.now(timezone.utc)
            session.add(draft)
            updated.append(draft)

    if not created and not updated:
        raise DraftError(
            "No links to send: they're marked removed or already in the draft"
        )

    # one commit for everything, so it's all or nothing
    session.commit()
    for draft in [*created, *updated]:
        session.refresh(draft)
    return created, updated


# --- reading ---


def get_takedown_email(
    *, session: Session, email_id: uuid.UUID
) -> TakedownEmail | None:
    return session.get(TakedownEmail, email_id)


def list_takedown_emails(
    *,
    session: Session,
    case_id: uuid.UUID | None = None,
    status: EmailStatus | None = None,
) -> list[TakedownEmail]:
    """Newest first, optionally for one case and/or one status."""
    query = select(TakedownEmail).order_by(col(TakedownEmail.created_at).desc())
    if case_id is not None:
        query = query.where(TakedownEmail.case_id == case_id)
    if status is not None:
        query = query.where(TakedownEmail.status == status)
    return list(session.exec(query))


def render_email_body(email: TakedownEmail) -> str:
    """The text to show / send: frozen after sending, else edited, else generated."""
    if email.sent_body is not None:
        return email.sent_body
    if email.custom_body is not None:
        return email.custom_body
    return generated_body(email)


def generated_body(email: TakedownEmail) -> str:
    """The body the template makes from the email's current links and grounds."""
    return render_body(
        full_name=email.case.profile.full_name,
        recipient_name=email.recipient_name,
        links=[LinkInput(link.url, link.domain) for link in _sorted_links(email.links)],
        legal_grounds=[
            GroundInput(g.citation, g.clause_text)
            for g in _sorted_grounds(email.legal_grounds)
        ],
        is_minor=email.case.is_minor,
    )


def to_public(email: TakedownEmail) -> TakedownEmailPublic:
    """Build the response, including the body (which isn't a column)."""
    return TakedownEmailPublic(
        id=email.id,
        case_id=email.case_id,
        recipient_id=email.recipient_id,
        recipient_name=email.recipient_name,
        relation=email.relation,
        email_type=email.email_type,
        to_address=email.to_address,
        subject=email.subject,
        body=render_email_body(email),
        is_body_custom=email.custom_body is not None,
        links=[CaseLinkPublic.model_validate(x) for x in _sorted_links(email.links)],
        legal_grounds=[
            LegalGroundPublic.model_validate(g)
            for g in _sorted_grounds(email.legal_grounds)
        ],
        status=email.status,
        attempts=email.attempts,
        last_error=email.last_error,
        sent_at=email.sent_at,
        created_at=email.created_at,
    )


# --- editing ---


def update_takedown_email(
    *, session: Session, db_email: TakedownEmail, email_in: TakedownEmailUpdate
) -> TakedownEmail:
    """Edit a draft. The route checks it's still a draft first."""
    update_data = email_in.model_dump(exclude_unset=True)

    # the two id lists aren't columns: swap them for the actual rows
    link_ids = update_data.pop("link_ids", None)
    ground_ids = update_data.pop("legal_ground_ids", None)

    if link_ids is not None:
        links = list(
            session.exec(select(CaseLink).where(col(CaseLink.id).in_(link_ids)))
        )
        # every id must exist and belong to this email's case
        if len(links) != len(set(link_ids)) or any(
            link.case_id != db_email.case_id for link in links
        ):
            raise DraftError("Some links don't belong to this case")
        if not links:
            raise DraftError("An email needs at least one link")
        db_email.links = links

    if ground_ids is not None:
        grounds = list(
            session.exec(select(LegalGround).where(col(LegalGround.id).in_(ground_ids)))
        )
        if len(grounds) != len(set(ground_ids)):
            raise DraftError("Some legal grounds don't exist")
        db_email.legal_grounds = grounds

    # a body that matches the template (e.g. sent back untouched) isn't an edit,
    # so keep it generated. Checked after the links/grounds above are applied
    custom_body = update_data.get("custom_body")
    if (
        custom_body is not None
        and custom_body.strip() == generated_body(db_email).strip()
    ):
        update_data["custom_body"] = None

    db_email.sqlmodel_update(update_data)
    db_email.updated_at = datetime.now(timezone.utc)
    session.add(db_email)
    session.commit()
    session.refresh(db_email)
    return db_email


def delete_takedown_email(*, session: Session, db_email: TakedownEmail) -> None:
    # the link table rows go with it (ondelete CASCADE / the relationship)
    session.delete(db_email)
    session.commit()
