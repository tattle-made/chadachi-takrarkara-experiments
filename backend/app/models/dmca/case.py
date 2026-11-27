"""Cases and their links.

- Case: one takedown effort for a profile (e.g. "Videos found in March"). Has
  is_minor, which switches its emails to the CSAM variant, and an optional
  assignee for the "Assigned to me" filter.
- CaseLink: one reported URL in a case, with its domain pulled out so we can find
  who to email. removed_at is set once the site has taken the link down.

Every counsellor sees every case; "Assigned to me" is only a filter.
"""

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlmodel import Column, Field, Relationship, SQLModel, UniqueConstraint

from app.models.dmca.profile import Profile, ProfileBase, ProfileSummary
from app.models.user import User


class CaseBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    is_minor: bool = False


class Case(CaseBase, table=True):
    # "case" alone is a reserved word in SQL; with the prefix it is fine
    __tablename__ = "dmca_case"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # CASCADE: deleting a profile deletes its cases (and their links)
    profile_id: uuid.UUID = Field(
        foreign_key="dmca_profile.id", ondelete="CASCADE", index=True
    )
    # SET NULL: if the user row ever goes, the case just becomes unassigned
    assigned_to: int | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", index=True
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

    profile: Profile = Relationship(back_populates="cases")
    # Case has two foreign keys to user (assigned_to and created_by), so we tell
    # SQLAlchemy which one this relationship uses
    assignee: User | None = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Case.assigned_to]"}
    )
    links: list["CaseLink"] = Relationship(back_populates="case", cascade_delete=True)


class CaseLink(SQLModel, table=True):
    __tablename__ = "dmca_case_link"
    # the same URL pasted twice into one case is skipped, not stored twice
    __table_args__ = (
        UniqueConstraint("case_id", "url", name="uq_dmca_case_link_case_url"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    case_id: uuid.UUID = Field(
        foreign_key="dmca_case.id", ondelete="CASCADE", index=True
    )
    url: str = Field(max_length=2048)
    # e.g. "example-site.com", from utils/links.extract_domain
    domain: str = Field(max_length=255, index=True)
    # set when someone marks the link removed (the site took it down)
    removed_at: datetime | None = Field(
        default=None, sa_column=Column(sa.DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )

    case: Case = Relationship(back_populates="links")


# --- API schemas ---


# who a case is assigned to. Users have no name field, so the email is the label
class UserSummary(SQLModel):
    id: int
    email: str


# body of POST /dmca/profiles/{id}/cases (profile_id comes from the URL)
class CaseCreate(CaseBase):
    assigned_to: int | None = None


# body of PATCH /dmca/cases/{id}. Send "assigned_to": null to unassign
class CaseUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    is_minor: bool | None = None
    assigned_to: int | None = None


class CaseLinkPublic(SQLModel):
    id: uuid.UUID
    url: str
    domain: str
    removed_at: datetime | None
    created_at: datetime


# a case in lists: who it's for and who has it, but not its links
class CaseSummary(CaseBase):
    id: uuid.UUID
    created_at: datetime
    profile: ProfileSummary
    assignee: UserSummary | None


class CasesPublic(SQLModel):
    data: list[CaseSummary]
    count: int


# GET /dmca/cases/{id}: the case with its links
class CasePublic(CaseSummary):
    links: list[CaseLinkPublic] = []


# a case inside ProfileDetail (the profile is already the parent)
class ProfileCase(CaseBase):
    id: uuid.UUID
    created_at: datetime
    assignee: UserSummary | None


# GET /dmca/profiles/{id}: the profile with its cases. Defined here, not in
# profile.py, because it needs ProfileCase
class ProfileDetail(ProfileBase):
    id: uuid.UUID
    created_at: datetime
    cases: list[ProfileCase] = []


# body of POST /dmca/cases/{id}/links: the text the counsellor pasted
class CaseLinksAdd(SQLModel):
    text: str = Field(min_length=1)


# what POST /dmca/cases/{id}/links returns
class CaseLinksAdded(SQLModel):
    added: list[CaseLinkPublic]
    # already in this case (or pasted twice)
    skipped: list[str]
    # not a link we could read a domain from
    invalid: list[str]
