"""Config tables: who we send takedown emails to.

- Recipient: an organisation (Cloudflare, Example Site Ltd, ...).
- RecipientEmail: its addresses, each with a type (dmca / abuse / csam / general).
- Domain: a site we see in reported links (example-site.com).
- DomainRecipient: which recipient plays which relation for a domain
  (Cloudflare is the cdn for example-site.com).

Each model has a *Base (fields shared with the API schemas) and a table=True class
(the DB table, adding id, foreign keys, timestamps and relationships).
Validators run only through Model.model_validate(...), not Model(...), so create
rows with model_validate when normalising matters.
"""

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from pydantic import computed_field, field_validator
from sqlmodel import Column, Field, Relationship, SQLModel, UniqueConstraint

from app.models.dmca.enums import DomainRelation, EmailType


class RecipientBase(SQLModel):
    name: str = Field(max_length=255)
    # free text for admins, e.g. "replies slowly, cc legal@"
    notes: str | None = None


class Recipient(RecipientBase, table=True):
    # default_factory runs when the object is created in Python, so the id exists
    # before the row is committed
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # sa_column with DateTime(timezone=True) makes it a timezone-aware column
    # (timestamptz in Postgres); the plain Field default would drop the timezone
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )

    # Relationships aren't columns: they let us write recipient.emails and get the
    # related rows (loaded on first access). back_populates links the two sides,
    # so email.recipient points back here.
    # emails and domain links belong to the recipient, so they go when it's deleted
    emails: list["RecipientEmail"] = Relationship(
        back_populates="recipient", cascade_delete=True
    )
    domain_links: list["DomainRecipient"] = Relationship(
        back_populates="recipient", cascade_delete=True
    )


class RecipientEmailBase(SQLModel):
    # indexed because we look emails up by address
    address: str = Field(max_length=255, index=True)
    email_type: EmailType

    # emails are case-insensitive, so store one form for the unique check to work
    @field_validator("address")
    @classmethod
    def normalise_address(cls, v: str) -> str:
        return v.strip().lower()


class RecipientEmail(RecipientEmailBase, table=True):
    __tablename__ = "recipient_email"
    # one address can serve several types (e.g. the same inbox for DMCA and abuse),
    # but an address + type belongs to only one recipient. The unique index is on
    # lower(address), so the DB also catches case variants inserted directly.
    __table_args__ = (
        sa.Index(
            "uq_recipient_email_lower_address_type",
            sa.text("lower(address)"),
            "email_type",
            unique=True,
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # set from the URL (/recipients/{id}/emails), so it's not in the Base.
    # ondelete="CASCADE" makes the DB itself delete emails of a deleted recipient
    recipient_id: uuid.UUID = Field(
        foreign_key="recipient.id", ondelete="CASCADE", index=True
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )

    recipient: Recipient = Relationship(back_populates="emails")


class DomainBase(SQLModel):
    # unique via the lower(domain) index on Domain
    domain: str = Field(max_length=255, index=True)

    @field_validator("domain")
    @classmethod
    def normalise_domain(cls, v: str) -> str:
        return v.strip().lower()


class Domain(DomainBase, table=True):
    # one row per site, shared by every recipient linked to it
    __table_args__ = (
        sa.Index("uq_domain_lower_domain", sa.text("lower(domain)"), unique=True),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )

    recipient_links: list["DomainRecipient"] = Relationship(
        back_populates="domain", cascade_delete=True
    )


class DomainRecipient(SQLModel, table=True):
    """How a recipient relates to a domain, e.g. Cloudflare is the cdn for example-site.com."""

    __tablename__ = "domain_recipient"
    # the same recipient can have several relations for one domain (e.g. host and
    # cdn), but each relation only once
    __table_args__ = (
        UniqueConstraint(
            "domain_id",
            "recipient_id",
            "relation",
            name="uq_domain_recipient_domain_recipient_relation",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    domain_id: uuid.UUID = Field(
        foreign_key="domain.id", ondelete="CASCADE", index=True
    )
    recipient_id: uuid.UUID = Field(
        foreign_key="recipient.id", ondelete="CASCADE", index=True
    )
    relation: DomainRelation
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )

    domain: Domain = Relationship(back_populates="recipient_links")
    recipient: Recipient = Relationship(back_populates="domain_links")


# --- API schemas ---
# Inputs (Create / Update) and outputs (Public). Outputs are built straight from
# the table objects with Model.model_validate(row), following the relationships.


# body of POST /recipients
class RecipientCreate(RecipientBase):
    pass


class RecipientUpdate(SQLModel):
    # every field optional, so a PATCH can change just one of them
    name: str | None = Field(default=None, max_length=255)
    notes: str | None = None


# body of POST /recipients/{id}/emails (recipient_id comes from the URL)
class RecipientEmailCreate(RecipientEmailBase):
    pass


class RecipientEmailPublic(RecipientEmailBase):
    id: uuid.UUID


class DomainPublic(DomainBase):
    id: uuid.UUID


class DomainLinkCreate(DomainBase):
    """Body of POST /recipients/{id}/domains: the domain is found or created by name."""

    relation: DomainRelation


# one domain link inside RecipientPublic, with the domain nested in it
class DomainLinkPublic(SQLModel):
    id: uuid.UUID
    relation: DomainRelation
    domain: DomainPublic


# what GET /recipients/{id} returns. emails and domain_links are filled from the
# relationships of the same name; fields not listed here (updated_at,
# recipient_id, ...) are left out of the response
class RecipientPublic(RecipientBase):
    id: uuid.UUID
    created_at: datetime
    emails: list[RecipientEmailPublic] = []
    domain_links: list[DomainLinkPublic] = []


# list response: one page of recipients + the total, for pagination
class RecipientsPublic(SQLModel):
    data: list[RecipientPublic]
    count: int


# --- GET /domains/resolve ---


# just enough to show and pick a recipient on the review screen; the full
# RecipientPublic would be too much per domain
class RecipientSummary(SQLModel):
    id: uuid.UUID
    name: str
    # read from recipient.emails when built from a row, but left out of the
    # response (exclude=True); only email_types below is sent
    emails: list[RecipientEmailPublic] = Field(default=[], exclude=True)

    # @computed_field: worked out from other fields and included in the response
    # like a normal field. @property makes it read like an attribute
    @computed_field  # type: ignore[prop-decorator]
    @property
    def email_types(self) -> list[EmailType]:
        """The types this recipient has an address for, for the review screen's
        email type dropdown. Unique, in EmailType order (dmca, abuse, csam, general).
        """
        have = {email.email_type for email in self.emails}
        return [t for t in EmailType if t in have]


class ResolvedLink(SQLModel):
    id: uuid.UUID
    relation: DomainRelation
    recipient: RecipientSummary


# one entry per domain asked for, with the recipients linked to it
class DomainResolved(DomainBase):
    # empty for a domain that isn't in Config yet
    recipient_links: list[ResolvedLink] = []
