"""Sending an email through the connected Gmail account.

send_message() is the only code that calls Gmail's send. Outside production it
always swaps the recipient for EMAIL_REDIRECT_TO, so dev and staging can't
email real organizations' accounts.
"""

import io
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import make_msgid

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build  # type: ignore[import-untyped]
from googleapiclient.http import MediaIoBaseUpload  # type: ignore[import-untyped]

from app.core.config import settings
from app.services.storage import StoredFile


@dataclass
class OutgoingEmail:
    to: str
    subject: str
    body: str
    attachments: list[StoredFile] = field(default_factory=list)


@dataclass
class SentMessage:
    gmail_message_id: str
    # the Message-ID header we set, for finding the email in a mailbox later
    rfc822_message_id: str


def redirected(to: str, subject: str) -> tuple[str, str]:
    """Where the email really goes, and its subject.

    In production: unchanged. Elsewhere: to EMAIL_REDIRECT_TO, with the real
    address in the subject, e.g. "[TEST → dmca@host.com] DMCA Takedown Request".
    """
    if settings.ENVIRONMENT == "production":
        return to, subject
    if not settings.EMAIL_REDIRECT_TO:
        # config.py already refuses to start like this; checked again here
        # because this is the last stop before a real email goes out
        raise RuntimeError("EMAIL_REDIRECT_TO isn't set; not sending")
    return settings.EMAIL_REDIRECT_TO, f"[TEST → {to}] {subject}"


def build_message(email: OutgoingEmail) -> EmailMessage:
    """The email as Gmail expects it: plain-text body plus file attachments.
    From is left out; Gmail fills in the connected account."""
    to, subject = redirected(email.to, email.subject)
    message = EmailMessage()
    message["To"] = to
    message["Subject"] = subject
    message["Message-ID"] = make_msgid()
    message.set_content(email.body)
    for file in email.attachments:
        # "application/pdf" -> maintype "application", subtype "pdf"
        maintype, _, subtype = file.mime_type.partition("/")
        message.add_attachment(
            file.data,
            maintype=maintype or "application",
            subtype=subtype or "octet-stream",
            filename=file.name,
        )
    return message


def send_message(creds: Credentials, email: OutgoingEmail) -> SentMessage:
    """Send it. Raises googleapiclient's HttpError if Gmail refuses."""
    message = build_message(email)
    # sent as an upload, not inside the JSON request ({"raw": ...}): Google caps
    # the JSON request size, uploads go up to 35 MB
    upload = MediaIoBaseUpload(
        io.BytesIO(message.as_bytes()), mimetype="message/rfc822", resumable=True
    )
    gmail = build("gmail", "v1", credentials=creds, cache_discovery=False)
    sent = gmail.users().messages().send(userId="me", media_body=upload).execute()
    return SentMessage(
        gmail_message_id=sent["id"], rfc822_message_id=message["Message-ID"]
    )
