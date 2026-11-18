"""Takedown emails: one email to one recipient about some of a case's links.

Created as drafts from the review screen (POST /dmca/cases/{id}/drafts), edited
while they're drafts, then sent by the background sender. After sending nothing changes: the
final text is frozen in sent_body, which is the record of what went out.

Three link tables connect an email to:
- the case links it covers (takedown_email_link)
- the legal grounds it cites (takedown_email_legal_ground)
- the profile documents sent with it (takedown_email_attachment_join)
RESTRICT on the last two means the DB refuses to delete a ground or a document
that an email uses.

The body isn't stored while it's a draft unless someone edits it: custom_body is
None means "generate it from the template", so fixes to a legal ground's text
show up in drafts that haven't been edited.
"""

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlmodel import Column, Field, Relationship, SQLModel

from app.models.dmca.attachment import Attachment, AttachmentPublic
from app.models.dmca.case import Case, CaseLink, CaseLinkPublic
from app.models.dmca.enums import DomainRelation, EmailStatus, EmailType
from app.models.dmca.legal_ground import LegalGround, LegalGroundPublic

# --- link tables (many-to-many) ---
# An email covers many links and a link can be in many emails (e.g. a first email
# to the site, then an escalation to its host), so they're joined by a table of
# (email_id, link_id) pairs. Same for legal grounds.


class TakedownEmailLink(SQLModel, table=True):
    __tablename__ = "takedown_email_link"

    # both columns together are the primary key: each pair only once
    email_id: uuid.UUID = Field(
        foreign_key="takedown_email.id", ondelete="CASCADE", primary_key=True
    )
    link_id: uuid.UUID = Field(
        foreign_key="case_link.id", ondelete="CASCADE", primary_key=True
    )


class TakedownEmailLegalGround(SQLModel, table=True):
    __tablename__ = "takedown_email_legal_ground"

    email_id: uuid.UUID = Field(
        foreign_key="takedown_email.id", ondelete="CASCADE", primary_key=True
    )
    # RESTRICT: a ground that an email uses can't be deleted (turn it off instead)
    legal_ground_id: uuid.UUID = Field(
        foreign_key="legal_ground.id", ondelete="RESTRICT", primary_key=True
    )


class TakedownEmailAttachmentJoin(SQLModel, table=True):
    __tablename__ = "takedown_email_attachment_join"

    email_id: uuid.UUID = Field(
        foreign_key="takedown_email.id", ondelete="CASCADE", primary_key=True
    )
    attachment_id: uuid.UUID = Field(
        foreign_key="attachment.id", ondelete="RESTRICT", primary_key=True
    )


# --- the email ---


class TakedownEmail(SQLModel, table=True):
    __tablename__ = "takedown_email"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    case_id: uuid.UUID = Field(
        foreign_key="takedown_case.id", ondelete="CASCADE", index=True
    )

    # who it goes to. Becomes None if the recipient is deleted in Config
    recipient_id: uuid.UUID | None = Field(
        default=None, foreign_key="recipient.id", ondelete="SET NULL", index=True
    )
    # a copy of the recipient's name, so it's still here if the recipient is deleted
    recipient_name: str = Field(max_length=255)
    # the step this email is for (website_owner, cdn, ...): Escalate suggests the
    # next one. None for a recipient picked by hand
    relation: DomainRelation | None = None
    # which of the recipient's addresses it uses (the review screen's dropdown).
    # None if the recipient has no address yet; to_address is then filled by hand
    email_type: EmailType | None = None
    to_address: str | None = Field(default=None, max_length=255)

    subject: str = Field(max_length=500)
    # None = generated from the template; a string = edited by the counsellor
    custom_body: str | None = None

    status: EmailStatus = Field(default=EmailStatus.draft, index=True)
    # filled in by the background sender when it sends the email
    attempts: int = 0
    last_error: str | None = None
    sent_body: str | None = None
    gmail_message_id: str | None = Field(default=None, max_length=255)
    rfc822_message_id: str | None = Field(default=None, max_length=255)
    sent_at: datetime | None = Field(
        default=None, sa_column=Column(sa.DateTime(timezone=True), nullable=True)
    )
    # when the counsellor marked "Got a reply" (they check replies in Gmail).
    # None = no reply marked
    reply_received_at: datetime | None = Field(
        default=None, sa_column=Column(sa.DateTime(timezone=True), nullable=True)
    )

    created_by: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )

    case: Case = Relationship()
    # link_model= tells SQLModel to go through the link table. email.links is a
    # plain list of CaseLink; assigning a new list updates the link table
    links: list[CaseLink] = Relationship(link_model=TakedownEmailLink)
    legal_grounds: list[LegalGround] = Relationship(link_model=TakedownEmailLegalGround)
    attachments: list[Attachment] = Relationship(link_model=TakedownEmailAttachmentJoin)


# --- API schemas ---


class DraftItem(SQLModel):
    """One row of the review screen: send this domain's links to this recipient."""

    domain: str
    recipient_id: uuid.UUID
    # the dropdown's choice. Left out = the default order (dmca -> abuse ->
    # general, or csam -> dmca -> abuse -> general for a minor case)
    email_type: EmailType | None = None
    # the recipient's relation to this domain, from /domains/resolve. Left out
    # for a recipient picked by hand
    relation: DomainRelation | None = None
    # add the links to this existing draft (same case and recipient) instead of
    # making a new email. Its body is reset to the template so they show up
    add_to_email_id: uuid.UUID | None = None


# body of POST /dmca/cases/{id}/drafts
class DraftsCreate(SQLModel):
    items: list[DraftItem] = Field(min_length=1)


# body of PATCH /dmca/emails/{id}. Every field optional; only while it's a draft
class TakedownEmailUpdate(SQLModel):
    to_address: str | None = Field(default=None, max_length=255)
    subject: str | None = Field(default=None, min_length=1, max_length=500)
    # send null to throw away the edits and go back to the generated body
    custom_body: str | None = None
    # replace the whole list (ids must belong to this case / exist)
    link_ids: list[uuid.UUID] | None = None
    legal_ground_ids: list[uuid.UUID] | None = None
    # ids of the profile's documents to send with it (replaces the whole list)
    attachment_ids: list[uuid.UUID] | None = None


class TakedownEmailPublic(SQLModel):
    id: uuid.UUID
    case_id: uuid.UUID
    recipient_id: uuid.UUID | None
    recipient_name: str
    relation: DomainRelation | None
    email_type: EmailType | None
    to_address: str | None
    subject: str
    # what will be (or was) sent: sent_body, else custom_body, else generated
    body: str
    is_body_custom: bool
    links: list[CaseLinkPublic]
    legal_grounds: list[LegalGroundPublic]
    attachments: list[AttachmentPublic]
    status: EmailStatus
    # how many times sending was tried in total (for display)
    attempts: int
    last_error: str | None
    # failed, or stuck in "sending": the UI shows a Retry button
    can_retry: bool
    sent_at: datetime | None
    reply_received_at: datetime | None
    # sent over 48 hours ago and no reply marked (the UI shows "No reply · 48h+")
    no_reply_48h: bool
    created_at: datetime


# body of PUT /dmca/emails/{id}/reply-received: mark or unmark "Got a reply"
class EmailReplyReceived(SQLModel):
    received: bool


# one row of GET /dmca/emails/{id}/escalation: a site in the email, and who to
# email next about it (a suggestion; the review screen lets them pick anyone)
class EscalationSuggestion(SQLModel):
    domain: str
    # None: nobody further along the chain for this site
    recipient_id: uuid.UUID | None = None
    recipient_name: str | None = None
    relation: DomainRelation | None = None


# what POST /dmca/cases/{id}/drafts returns: new drafts, and existing ones that
# got more links
class DraftsResult(SQLModel):
    created: list[TakedownEmailPublic]
    updated: list[TakedownEmailPublic]


# body of POST /dmca/emails/send
class EmailsSend(SQLModel):
    email_ids: list[uuid.UUID] = Field(min_length=1)
