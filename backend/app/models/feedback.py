import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlmodel import Column, Field, Relationship, SQLModel

from app.models.enums import AnnotationTag
from app.models.message import Message
from app.models.user import User


class FeedbackBase(SQLModel):
    message_id: uuid.UUID = Field(foreign_key="message.id", ondelete="CASCADE")
    user_id: int = Field(foreign_key="user.id", ondelete="CASCADE")
    # snapshot of the full text at annotation time for audit integrity
    text_snapshot: str
    comment: str | None = None


class Feedback(FeedbackBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )

    message: Message = Relationship(back_populates="feedback")
    user: User = Relationship(back_populates="feedback")
    spans: list["AnnotationSpan"] = Relationship(back_populates="feedback")


class FeedbackCreate(FeedbackBase):
    spans: list["AnnotationSpanCreate"]


class FeedbackPublic(FeedbackBase):
    id: uuid.UUID
    created_at: datetime
    spans: list["AnnotationSpanPublic"]


class AnnotationSpanBase(SQLModel):
    feedback_id: uuid.UUID = Field(foreign_key="feedback.id", ondelete="CASCADE")
    start_offset: int
    end_offset: int
    highlighted_text: str
    # stored as VARCHAR so Python enum values (e.g. "too-verbose") roundtrip correctly
    tag: AnnotationTag = Field(sa_column=Column(sa.String(), nullable=False))


class AnnotationSpan(AnnotationSpanBase, table=True):
    __tablename__ = "annotation_span"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    feedback: Feedback = Relationship(back_populates="spans")


class AnnotationSpanCreate(AnnotationSpanBase):
    feedback_id: uuid.UUID | None = None  # set by create_feedback after flush


class AnnotationSpanPublic(AnnotationSpanBase):
    id: uuid.UUID
