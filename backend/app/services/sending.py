"""Sending one takedown email: the work the background queue does for each job.

Status: queued -> sending -> sent, or failed. A temporary problem (Gmail rate
limit, Google down, network) puts it back to queued and raises RetryableSendError
so the queue tries again later; anything else, or running out of tries, is failed.
"""

import uuid
from datetime import datetime, timezone

from sqlmodel import Session

from app.crud.dmca.takedown_email import render_email_body
from app.models.dmca.enums import EmailStatus
from app.models.dmca.takedown_email import TakedownEmail
from app.services.gmail import OutgoingEmail, send_message
from app.services.google_auth import get_credentials
from app.services.google_errors import describe, is_retryable
from app.services.storage import get_storage


class RetryableSendError(Exception):
    """A temporary problem; the queue should try this email again later."""


def send_email(*, session: Session, email_id: uuid.UUID, last_try: bool) -> None:
    """Send one queued email and record the result on it.

    last_try: the queue has no retries left, so a temporary problem fails it too.
    Does nothing if the email is gone or isn't waiting to be sent. An email left
    in "sending" (the app stopped mid-send) is tried again.
    """
    email = session.get(TakedownEmail, email_id)
    if email is None or email.status not in (EmailStatus.queued, EmailStatus.sending):
        return

    email.status = EmailStatus.sending
    email.attempts += 1
    # when this try started; "sending" long after this means it got stuck
    email.updated_at = datetime.now(timezone.utc)
    session.add(email)
    session.commit()

    loading: str | None = None
    try:
        if not email.to_address:
            raise ValueError("No To address; add one to the draft and retry")
        body = render_email_body(email)
        storage = get_storage(session=session)
        files = []
        for attachment in email.attachments:
            # remembered so an error here can name the document
            loading = attachment.file_name
            files.append(storage.get(attachment.storage_key))
        loading = None
        sent = send_message(
            get_credentials(session=session),
            OutgoingEmail(
                to=email.to_address,
                subject=email.subject,
                body=body,
                attachments=files,
            ),
        )
    except Exception as err:
        retry = is_retryable(err) and not last_try
        email.status = EmailStatus.queued if retry else EmailStatus.failed
        email.last_error = describe(err)
        if loading:
            email.last_error = (
                f"Couldn't load the document '{loading}': {email.last_error}"
            )
        email.updated_at = datetime.now(timezone.utc)
        session.add(email)
        session.commit()
        if retry:
            raise RetryableSendError(email.last_error) from err
        return

    # frozen: the record of exactly what went out
    email.sent_body = body
    email.status = EmailStatus.sent
    email.sent_at = datetime.now(timezone.utc)
    email.gmail_message_id = sent.gmail_message_id
    email.rfc822_message_id = sent.rfc822_message_id
    email.last_error = None
    email.updated_at = email.sent_at
    session.add(email)
    session.commit()
