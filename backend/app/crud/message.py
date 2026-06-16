from datetime import datetime, timezone

from sqlmodel import Session

from app.models.conversation import Conversation
from app.models.message import Message, MessageCreate


def create_message(*, session: Session, message_in: MessageCreate) -> Message:
    db_message = Message.model_validate(message_in)
    session.add(db_message)
    conversation = session.get(Conversation, message_in.conversation_id)
    if conversation:
        conversation.updated_at = datetime.now(timezone.utc)
        session.add(conversation)
    session.commit()
    session.refresh(db_message)
    return db_message
