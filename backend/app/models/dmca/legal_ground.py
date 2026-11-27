"""Legal grounds: the law clauses a counsellor can tick on a takedown email.

The template lists the ticked ones under "This incident breaches ... along with
the following:". Admins manage the list in Config.

A ground can be deleted only while no email uses it (e.g. one added by mistake).
Once emails use it, it can only be turned off (active=False), so sent emails keep
pointing to the grounds they used. Edits are fine: a sent email keeps its own
stored body, so the text it went out with doesn't change.
"""

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlmodel import Column, Field, SQLModel


class LegalGroundBase(SQLModel):
    # short name shown in the picker
    title: str = Field(min_length=1, max_length=255)
    # e.g. "Section 66E, IT Act 2000"
    citation: str = Field(min_length=1, max_length=255)
    # the sentence that goes into the email body
    clause_text: str = Field(min_length=1)
    # ticked by default on a new draft
    default_selected: bool = False
    # only offered on minor (CSAM) cases
    minor_only: bool = False
    # False hides it from new drafts without deleting it
    active: bool = True


class LegalGround(LegalGroundBase, table=True):
    __tablename__ = "dmca_legal_ground"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )


# --- API schemas ---


# body of POST /dmca/legal-grounds
class LegalGroundCreate(LegalGroundBase):
    pass


# body of PATCH /dmca/legal-grounds/{id}: every field optional, so a PATCH can
# change just one (e.g. {"active": false} to turn a ground off)
class LegalGroundUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    citation: str | None = Field(default=None, min_length=1, max_length=255)
    clause_text: str | None = Field(default=None, min_length=1)
    default_selected: bool | None = None
    minor_only: bool | None = None
    active: bool | None = None


class LegalGroundPublic(LegalGroundBase):
    id: uuid.UUID
    created_at: datetime


# list response: the grounds + how many
class LegalGroundsPublic(SQLModel):
    data: list[LegalGroundPublic]
    count: int
