"""Profiles: the person a takedown is for.

A profile holds who the person is; the work happens in their cases (see case.py).
One person can have several cases over time.

Two names:
- full_name: the legal name. It goes into the email body ("<full_name> is the
  exclusive rights holder ...") and is shown on the profile page.
- display_name: optional internal label (initials, a case code, ...) shown in
  lists and search instead, so the real name isn't on every screen. The UI falls
  back to full_name when it's empty.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import sqlalchemy as sa
from pydantic import field_validator
from sqlmodel import Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    # only for type checkers; at runtime SQLModel finds Case by its name
    from app.models.dmca.case import Case


class ProfileBase(SQLModel):
    full_name: str = Field(min_length=1, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)
    notes: str | None = None

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, v: str) -> str:
        return v.strip()

    # a blank display name means "none", so the UI falls back to full_name
    @field_validator("display_name")
    @classmethod
    def blank_display_name_is_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return v.strip() or None


class Profile(ProfileBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # users are archived, never deleted, so a plain FK is enough here
    created_by: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )

    cases: list["Case"] = Relationship(back_populates="profile")


# --- API schemas ---
# ProfileDetail (a profile with its cases) lives in case.py, because it needs the
# case schemas and case.py already imports this file.


# body of POST /dmca/profiles
class ProfileCreate(ProfileBase):
    pass


# body of PATCH /dmca/profiles/{id}: every field optional
class ProfileUpdate(SQLModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)
    notes: str | None = None

    @field_validator("display_name")
    @classmethod
    def blank_display_name_is_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return v.strip() or None


# a profile in lists and inside a case (no notes, no cases)
class ProfileSummary(SQLModel):
    id: uuid.UUID
    full_name: str
    display_name: str | None
    created_at: datetime


class ProfilesPublic(SQLModel):
    data: list[ProfileSummary]
    count: int
