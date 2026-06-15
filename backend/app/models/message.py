import uuid
from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa
from sqlmodel import Column, Field, JSON, Relationship, SQLModel

from app.models.conversation import Conversation
from app.models.enums import FunctionalityType, MessageKind, MessageStatus


class MessageBase(SQLModel):
    conversation_id: uuid.UUID = Field(
        foreign_key="conversation.id", ondelete="CASCADE"
    )
    user_id: int = Field(foreign_key="user.id", ondelete="CASCADE")
    kind: MessageKind
    functionality_type: FunctionalityType
    body: str
    # links an LLM response back to the user query that triggered it
    parent_message_id: uuid.UUID | None = Field(
        default=None, foreign_key="message.id", ondelete="SET NULL"
    )
    model_name: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: int | None = None
    status: MessageStatus = MessageStatus.completed
    # feature-specific structured output (policy clauses, email draft, etc.)
    structured_output: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    is_deleted: bool = False
    error_detail: str | None = None


class Message(MessageBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )

    conversation: Conversation = Relationship(back_populates="messages")


class MessageCreate(MessageBase):
    pass


class MessagePublic(MessageBase):
    id: uuid.UUID
    created_at: datetime
