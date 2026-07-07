from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.models.feedback import (
    AnnotationSpan,
    AnnotationSpanCreate,
    Feedback,
    FeedbackCreate,
)


def get_all_feedback_for_export(*, session: Session) -> list[Feedback]:
    statement = (
        select(Feedback)
        .options(
            selectinload(Feedback.user),
            selectinload(Feedback.spans),
            selectinload(Feedback.message),
        )  # type: ignore[arg-type]
        .order_by(Feedback.created_at)
    )
    return list(session.exec(statement).all())


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


def update_feedback(
    *,
    session: Session,
    feedback: Feedback,
    comment: str | None,
    spans: list[AnnotationSpanCreate],
) -> Feedback:
    feedback.comment = comment

    old_spans = session.exec(
        select(AnnotationSpan).where(AnnotationSpan.feedback_id == feedback.id)
    ).all()

    for span in old_spans:
        session.delete(span)

    db_spans = [
        AnnotationSpan.model_validate(span, update={"feedback_id": feedback.id})
        for span in spans
    ]

    session.add(feedback)
    session.add_all(db_spans)
    session.commit()
    session.refresh(feedback)
    feedback.spans = db_spans

    return feedback
