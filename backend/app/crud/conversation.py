from sqlmodel import Session

from app.models.conversation import Conversation, ConversationCreate


def create_conversation(
    *, session: Session, conversation_in: ConversationCreate
) -> Conversation:
    db_conversation = Conversation.model_validate(conversation_in)
    session.add(db_conversation)
    session.commit()
    session.refresh(db_conversation)
    return db_conversation
