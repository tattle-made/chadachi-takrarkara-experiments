import csv
import io
import logging
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import select

logger = logging.getLogger(__name__)
from openai import OpenAI

from app import crud
from app.api.deps import AdminDep, CurrentUserDep, SessionDep
from app.core.config import settings
from app.models import (
    AnnotationTag,
    Conversation,
    ConversationCreate,
    FeedbackCreate,
    FunctionalityType,
    Message,
    MessageCreate,
    MessageKind,
    MessageStatus,
)
from app.models.email import (
    EmailFeedbackRequest,
    EmailFeedbackResponse,
    EmailGenerateRequest,
    EmailGenerateResponse,
)
from app.models.feedback import AnnotationSpanCreate

router = APIRouter(prefix="/email", tags=["email"])

_openai = OpenAI(api_key=settings.OPENAI_API_KEY)

WRITE_EMAIL_PROMPT = """\
I am a trust and safety expert whose job is to help support victims of cybercrimes.

Your task is to assist me in drafting emails to be sent to social media platforms based on the unique nuances of victim's case.

I have the case details of a victim here.

{case_details}

## Email Structure
The structure of the generated email should be like this:
(greetings from our team)
(summary of case details highlighting the impact on victim's wellbeing)
(elaborate all instances of abuse)
(insert a note if it is a repeat case)
(insert community guideline violations)
    Mention all Meta policy that can be applied to request takedown of the content.
    Cite verbatim snippet from the policy documents
(closing remark summarizing our ask)

# General instructions on the tone of the email
Keep your answer succinct. Be thorough in your search. It's more important to include all relevant clauses than to miss any relevant clause. Make sure the category of harms are in decreasing order of relevance. The most pertinent clause should come first. By pertinent we mean a policy that has implications of content takedown. Because the most serious action that the platform can take is content takedown. So if there's a policy that will lead to this content's takedown, that should come first.

Please be aware that I will add relevant evidence and attachments to this email, so you don't need to provide too much information about the details of the case.

Please also note that in no case should you include the name of any of the people mentioned in the case detail.
"""


@router.post("/generate", response_model=EmailGenerateResponse)
def generate_email(
    body: EmailGenerateRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> EmailGenerateResponse:
    conversation = crud.create_conversation(
        session=session,
        conversation_in=ConversationCreate(
            user_id=current_user.id,
            functionality_type=FunctionalityType.write_email,
        ),
    )

    crud.create_message(
        session=session,
        message_in=MessageCreate(
            conversation_id=conversation.id,
            user_id=current_user.id,
            kind=MessageKind.user_query,
            functionality_type=FunctionalityType.write_email,
            body=body.case_details,
        ),
    )

    prompt = WRITE_EMAIL_PROMPT.replace("{case_details}", body.case_details)

    start = time.monotonic()
    try:
        response = _openai.responses.create(
            model="gpt-4.1",
            input=prompt,
            tools=[
                {
                    "type": "file_search",
                    "vector_store_ids": [settings.OPENAI_VECTOR_STORE_ID],
                }
            ],
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        email_text = response.output_text

        llm_message = crud.create_message(
            session=session,
            message_in=MessageCreate(
                conversation_id=conversation.id,
                user_id=current_user.id,
                kind=MessageKind.llm_response,
                functionality_type=FunctionalityType.write_email,
                body=email_text,
                model_name="gpt-4.1",
                prompt_tokens=response.usage.input_tokens if response.usage else None,
                completion_tokens=response.usage.output_tokens
                if response.usage
                else None,
                latency_ms=latency_ms,
                status=MessageStatus.completed,
            ),
        )
    except Exception as e:
        logger.exception("OpenAI call failed: %s", e)
        latency_ms = int((time.monotonic() - start) * 1000)
        llm_message = crud.create_message(
            session=session,
            message_in=MessageCreate(
                conversation_id=conversation.id,
                user_id=current_user.id,
                kind=MessageKind.llm_response,
                functionality_type=FunctionalityType.write_email,
                body="",
                latency_ms=latency_ms,
                status=MessageStatus.error,
                error_detail=str(e),
            ),
        )
        raise HTTPException(status_code=502, detail="Failed to generate email") from e

    return EmailGenerateResponse(
        email=email_text,
        conversation_id=conversation.id,
        message_id=llm_message.id,
    )


@router.get("/feedback/export")
def export_feedback_csv(
    session: SessionDep,
    _: AdminDep,
) -> StreamingResponse:
    feedbacks = crud.get_all_feedback_for_export(session=session)

    conv_ids = {fb.message.conversation_id for fb in feedbacks}
    user_queries: dict = {}
    if conv_ids:
        rows = session.exec(
            select(Message).where(
                Message.conversation_id.in_(conv_ids),  # type: ignore[arg-type]
                Message.kind == MessageKind.user_query,
            )
        ).all()
        for msg in rows:
            user_queries[msg.conversation_id] = msg.body

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "feedback_id",
            "created_at",
            "user_email",
            "message_id",
            "user_query",
            "text_snapshot",
            "comment",
            "span_start",
            "span_end",
            "highlighted_text",
            "tag",
        ]
    )

    for fb in feedbacks:
        base = [
            str(fb.id),
            fb.created_at.isoformat(),
            fb.user.email,
            str(fb.message_id),
            user_queries.get(fb.message.conversation_id, ""),
            fb.text_snapshot,
            fb.comment or "",
        ]
        if fb.spans:
            for span in fb.spans:
                writer.writerow(
                    base
                    + [
                        span.start_offset,
                        span.end_offset,
                        span.highlighted_text,
                        span.tag,
                    ]
                )
        else:
            writer.writerow(base + ["", "", "", ""])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=feedback_export.csv"},
    )


@router.post("/feedback", response_model=EmailFeedbackResponse)
def submit_feedback(
    body: EmailFeedbackRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> EmailFeedbackResponse:
    message = session.get(Message, body.message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    conversation = session.get(Conversation, message.conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorised")

    try:
        spans = [
            AnnotationSpanCreate(
                start_offset=a.start,
                end_offset=a.end,
                highlighted_text=a.text,
                tag=AnnotationTag(a.tag),
            )
            for a in body.annotations
        ]
    except ValueError as e:
        raise HTTPException(
            status_code=422, detail=f"Invalid annotation tag: {e}"
        ) from e

    feedback = crud.create_feedback(
        session=session,
        feedback_in=FeedbackCreate(
            message_id=body.message_id,
            user_id=current_user.id,
            text_snapshot=message.body,
            comment=body.custom_comment,
            spans=spans,
        ),
    )

    return EmailFeedbackResponse(feedback_id=feedback.id)
