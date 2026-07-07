import uuid

from sqlmodel import Field, SQLModel


class EmailGenerateRequest(SQLModel):
    case_details: str = Field(max_length=50000)


class EmailGenerateResponse(SQLModel):
    email: str
    conversation_id: uuid.UUID
    message_id: uuid.UUID


class AnnotationInput(SQLModel):
    start: int
    end: int
    text: str
    tag: str


class EmailFeedbackRequest(SQLModel):
    message_id: uuid.UUID
    annotations: list[AnnotationInput]
    custom_comment: str | None = None


class EmailFeedbackResponse(SQLModel):
    feedback_id: uuid.UUID

class EmailFeedbackUpdateRequest(SQLModel):
    annotations: list[AnnotationInput]
    custom_comment: str | None = None