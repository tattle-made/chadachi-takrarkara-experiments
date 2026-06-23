from sqlmodel import Session

from app.models.feedback import AnnotationSpan, Feedback, FeedbackCreate


def create_feedback(*, session: Session, feedback_in: FeedbackCreate) -> Feedback:
    spans_data = feedback_in.spans
    db_feedback = Feedback(**feedback_in.model_dump(exclude={"spans"}))
    session.add(db_feedback)
    session.flush()  # get db_feedback.id before inserting spans

    db_spans = [
        AnnotationSpan.model_validate(span, update={"feedback_id": db_feedback.id})
        for span in spans_data
    ]
    session.add_all(db_spans)

    session.commit()
    session.refresh(db_feedback)
    db_feedback.spans = db_spans
    return db_feedback
