"""Tests for sending takedown emails: the Send / Retry routes, the work done for
each email (services/sending.py), the queue worker, and the Gmail message.

Gmail and the queue are never really called: send_message and enqueue_sends
are replaced with fakes.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

import httplib2  # type: ignore[import-untyped]
import pytest
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError  # type: ignore[import-untyped]
from oban.testing import process_job
from pydantic import ValidationError
from sqlmodel import Session

from app.core.config import Settings, settings
from app.crud.dmca.google_connection import get_connection, save_connection
from app.models import User
from app.models.dmca import EmailStatus, GoogleConnectionStatus, TakedownEmail
from app.services import sending
from app.services.gmail import OutgoingEmail, SentMessage, build_message, redirected
from app.services.google_auth import GoogleNotConnected
from app.services.queue import RETRY_DELAYS, SendEmailWorker
from app.services.google_errors import describe, is_retryable
from app.services.sending import RetryableSendError, send_email
from app.services.storage import StoredFile, memory_storage
from tests.conftest import auth_headers
from tests.test_emails import BASE, created, make_recipient, post, upload_doc


@pytest.fixture
def member(member_token) -> dict[str, str]:
    return auth_headers(member_token)


@pytest.fixture
def admin(admin_token) -> dict[str, str]:
    return auth_headers(admin_token)


@pytest.fixture
def google(session: Session, admin_user: User) -> None:
    """A connected Google account (its token is never used: Gmail is faked)."""
    save_connection(
        session=session,
        account_email="team@example.org",
        refresh_token="refresh-123",
        scopes=[],
        connected_by=admin_user.id,
    )


@pytest.fixture
def case(client, admin, member) -> dict:
    """A case with two links on two sites, each with its own recipient."""
    cf = make_recipient(
        client, admin, "Cloudflare", {"dmca": "dmca@cf.test"}, {"a.test": "cdn"}
    )
    host = make_recipient(
        client, admin, "Host Co", {"abuse": "abuse@host.test"}, {"b.test": "host"}
    )
    profile = post(client, member, "/profiles", {"full_name": "Jane Doe"})
    case = post(client, member, f"/profiles/{profile['id']}/cases", {"title": "May"})
    post(client, member, f"/cases/{case['id']}/links", {"text": "a.test/1 b.test/1"})
    return {"id": case["id"], "profile": profile["id"], "cf": cf, "host": host}


@pytest.fixture
def two_drafts(client, member, case) -> list[dict]:
    items = [
        {"domain": "a.test", "recipient_id": case["cf"]},
        {"domain": "b.test", "recipient_id": case["host"]},
    ]
    return created(client, member, case["id"], items)


@pytest.fixture
def enqueued(monkeypatch) -> list[uuid.UUID]:
    """The ids the routes hand to the queue (the real queue isn't running)."""
    ids: list[uuid.UUID] = []
    monkeypatch.setattr(
        "app.api.routes.dmca.emails.enqueue_sends",
        lambda email_ids: ids.extend(email_ids),
    )
    return ids


def queue_is_down(monkeypatch) -> None:
    """Make adding jobs fail, as when the queue isn't running."""

    def fail(email_ids):
        raise RuntimeError("queue not running")

    monkeypatch.setattr("app.api.routes.dmca.emails.enqueue_sends", fail)


def set_fields(session: Session, email_id: str, **fields) -> TakedownEmail:
    """Change an email directly in the DB, e.g. to fake a failed send."""
    email = session.get(TakedownEmail, uuid.UUID(email_id))
    assert email is not None
    for name, value in fields.items():
        setattr(email, name, value)
    session.add(email)
    session.commit()
    session.refresh(email)
    return email


def send(client, headers, ids):
    return client.post(f"{BASE}/emails/send", json={"email_ids": ids}, headers=headers)


def retry(client, headers, email_id):
    return client.post(f"{BASE}/emails/{email_id}/retry", headers=headers)


# --- POST /emails/send ---


def test_send_queues_the_drafts(client, member, google, two_drafts, enqueued):
    ids = [d["id"] for d in two_drafts]
    response = send(client, member, ids)
    assert response.status_code == 200, response.text
    assert {e["status"] for e in response.json()} == {"queued"}
    assert sorted(map(str, enqueued)) == sorted(ids)


def test_send_with_one_non_draft_sends_nothing(
    client, session: Session, member, google, two_drafts, enqueued
):
    set_fields(session, two_drafts[1]["id"], status=EmailStatus.sent)
    response = send(client, member, [d["id"] for d in two_drafts])
    assert response.status_code == 409
    assert "Host Co" in response.json()["detail"]
    assert enqueued == []
    first = session.get(TakedownEmail, uuid.UUID(two_drafts[0]["id"]))
    assert first is not None and first.status == EmailStatus.draft


def test_send_unknown_email_is_404(client, member, google, two_drafts, enqueued):
    response = send(client, member, [two_drafts[0]["id"], str(uuid.uuid4())])
    assert response.status_code == 404
    assert enqueued == []


def test_send_without_to_address_is_400(
    client, session: Session, member, google, two_drafts, enqueued
):
    set_fields(session, two_drafts[0]["id"], to_address="")
    assert send(client, member, [two_drafts[0]["id"]]).status_code == 400


def test_send_without_google_is_409(client, member, two_drafts, enqueued):
    response = send(client, member, [two_drafts[0]["id"]])
    assert response.status_code == 409
    assert "Google" in response.json()["detail"]


def test_send_with_broken_google_is_409(
    client, session: Session, member, google, two_drafts, enqueued
):
    connection = get_connection(session=session)
    assert connection is not None
    connection.status = GoogleConnectionStatus.broken
    session.add(connection)
    session.commit()
    assert send(client, member, [two_drafts[0]["id"]]).status_code == 409


def test_send_empty_list_is_422(client, member, google):
    assert send(client, member, []).status_code == 422


def test_send_when_queue_is_down_puts_drafts_back(
    client, session: Session, member, google, two_drafts, monkeypatch
):
    queue_is_down(monkeypatch)
    response = send(client, member, [d["id"] for d in two_drafts])
    assert response.status_code == 503
    for d in two_drafts:
        email = session.get(TakedownEmail, uuid.UUID(d["id"]))
        assert email is not None and email.status == EmailStatus.draft


def test_send_needs_login(client, two_drafts):
    assert send(client, {}, [two_drafts[0]["id"]]).status_code == 401


# --- POST /emails/{id}/retry ---


def test_retry_failed_email(
    client, session: Session, member, google, two_drafts, enqueued
):
    email_id = two_drafts[0]["id"]
    set_fields(session, email_id, status=EmailStatus.failed, last_error="boom")
    response = retry(client, member, email_id)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "queued"
    assert body["last_error"] is None
    assert body["can_retry"] is False
    assert [str(i) for i in enqueued] == [email_id]


def test_retry_draft_is_409(client, member, google, two_drafts, enqueued):
    assert retry(client, member, two_drafts[0]["id"]).status_code == 409
    assert enqueued == []


def test_retry_email_still_sending_is_409(
    client, session: Session, member, google, two_drafts, enqueued
):
    email_id = two_drafts[0]["id"]
    set_fields(
        session,
        email_id,
        status=EmailStatus.sending,
        updated_at=datetime.now(timezone.utc),
    )
    assert retry(client, member, email_id).status_code == 409


def test_retry_email_stuck_sending(
    client, session: Session, member, google, two_drafts, enqueued
):
    email_id = two_drafts[0]["id"]
    long_ago = datetime.now(timezone.utc) - timedelta(minutes=11)
    set_fields(session, email_id, status=EmailStatus.sending, updated_at=long_ago)
    assert retry(client, member, email_id).status_code == 200


def test_retry_when_queue_is_down_keeps_the_error(
    client, session: Session, member, google, two_drafts, monkeypatch
):
    email_id = two_drafts[0]["id"]
    set_fields(session, email_id, status=EmailStatus.failed, last_error="boom")
    queue_is_down(monkeypatch)
    assert retry(client, member, email_id).status_code == 503
    email = session.get(TakedownEmail, uuid.UUID(email_id))
    assert email is not None
    assert email.status == EmailStatus.failed
    assert email.last_error == "boom"


def test_can_retry_shows_on_failed_emails(
    client, session: Session, member, case, two_drafts
):
    set_fields(session, two_drafts[0]["id"], status=EmailStatus.failed)
    response = client.get(
        f"{BASE}/emails", params={"case_id": case["id"]}, headers=member
    )
    flags = {e["id"]: e["can_retry"] for e in response.json()}
    assert flags == {two_drafts[0]["id"]: True, two_drafts[1]["id"]: False}


# --- send_email: the work for one queued email ---


class FakeGmail:
    """Stands in for gmail.send_message: records what would have gone out."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.sent: list[OutgoingEmail] = []

    def __call__(self, creds, email: OutgoingEmail) -> SentMessage:
        if self.error:
            raise self.error
        self.sent.append(email)
        return SentMessage(gmail_message_id="gm-1", rfc822_message_id="<id@test>")


@pytest.fixture
def fake_gmail(monkeypatch) -> FakeGmail:
    """Fake Gmail, and skip fetching real Google credentials."""
    fake = FakeGmail()
    monkeypatch.setattr(sending, "send_message", fake)
    monkeypatch.setattr(sending, "get_credentials", lambda session: None)
    return fake


@pytest.fixture
def queued(client, session: Session, member, google, case, two_drafts) -> uuid.UUID:
    """A queued email to Cloudflare with one document attached."""
    email_id = two_drafts[0]["id"]
    doc = upload_doc(client, member, case["profile"])
    response = client.patch(
        f"{BASE}/emails/{email_id}", json={"attachment_ids": [doc]}, headers=member
    )
    assert response.status_code == 200, response.text
    set_fields(session, email_id, status=EmailStatus.queued)
    return uuid.UUID(email_id)


def http_error(status: int, body: dict | None = None) -> HttpError:
    content = json.dumps(body or {"error": {"message": "nope"}}).encode()
    return HttpError(httplib2.Response({"status": status}), content)


def saved(session: Session, email_id: uuid.UUID) -> TakedownEmail:
    """The email as it is in the DB now."""
    email = session.get(TakedownEmail, email_id)
    assert email is not None
    session.refresh(email)
    return email


def run(session: Session, email_id: uuid.UUID, last_try: bool = False) -> TakedownEmail:
    """send_email, then the email as saved."""
    send_email(session=session, email_id=email_id, last_try=last_try)
    return saved(session, email_id)


def test_send_email_success(session: Session, queued, fake_gmail):
    email = run(session, queued)
    assert email.status == EmailStatus.sent
    assert email.attempts == 1
    assert email.gmail_message_id == "gm-1"
    assert email.rfc822_message_id == "<id@test>"
    assert email.sent_at is not None
    assert email.last_error is None
    # what went out is what's on record
    [out] = fake_gmail.sent
    assert out.to == "dmca@cf.test"
    assert out.subject == email.subject
    assert out.body == email.sent_body
    assert [(f.name, f.data) for f in out.attachments] == [("report.pdf", b"fake pdf")]


def test_send_email_temporary_error_goes_back_to_queued(
    session: Session, queued, fake_gmail
):
    fake_gmail.error = http_error(503)
    with pytest.raises(RetryableSendError):
        run(session, queued)
    email = saved(session, queued)
    assert email.status == EmailStatus.queued
    assert email.attempts == 1
    assert email.last_error is not None and "503" in email.last_error


def test_send_email_temporary_error_on_last_try_fails(
    session: Session, queued, fake_gmail
):
    fake_gmail.error = http_error(503)
    email = run(session, queued, last_try=True)
    assert email.status == EmailStatus.failed


def test_send_email_permanent_error_fails(session: Session, queued, fake_gmail):
    fake_gmail.error = http_error(400)
    email = run(session, queued)
    assert email.status == EmailStatus.failed
    assert email.last_error is not None and "400" in email.last_error


def test_send_email_google_disconnected_fails(
    session: Session, queued, fake_gmail, monkeypatch
):
    def not_connected(session):
        raise GoogleNotConnected("Google isn't connected")

    monkeypatch.setattr(sending, "get_credentials", not_connected)
    email = run(session, queued)
    assert email.status == EmailStatus.failed
    assert email.last_error is not None and "reconnect" in email.last_error


def test_send_email_without_to_address_fails(session: Session, queued, fake_gmail):
    set_fields(session, str(queued), to_address="")
    email = run(session, queued)
    assert email.status == EmailStatus.failed
    assert fake_gmail.sent == []


def test_send_email_names_the_document_drive_failed_on(
    session: Session, queued, fake_gmail, monkeypatch
):
    def missing(key):
        raise http_error(404, {"error": {"message": "File not found: abc"}})

    monkeypatch.setattr(memory_storage, "get", missing)
    email = run(session, queued)
    assert email.status == EmailStatus.failed
    assert email.last_error == (
        "Couldn't load the document 'report.pdf': Google error 404: File not found: abc"
    )
    assert fake_gmail.sent == []


@pytest.mark.parametrize("status", [EmailStatus.draft, EmailStatus.sent])
def test_send_email_skips_emails_not_waiting(
    session: Session, queued, fake_gmail, status
):
    set_fields(session, str(queued), status=status)
    email = run(session, queued)
    assert email.status == status
    assert email.attempts == 0
    assert fake_gmail.sent == []


def test_send_email_unknown_id_does_nothing(session: Session, fake_gmail):
    send_email(session=session, email_id=uuid.uuid4(), last_try=False)
    assert fake_gmail.sent == []


def test_send_email_picks_up_one_left_sending(session: Session, queued, fake_gmail):
    set_fields(session, str(queued), status=EmailStatus.sending, attempts=1)
    email = run(session, queued)
    assert email.status == EmailStatus.sent
    assert email.attempts == 2


# --- which errors are worth a retry ---


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_retryable_status_codes(status):
    assert is_retryable(http_error(status))


@pytest.mark.parametrize("status", [400, 401, 404])
def test_not_retryable_status_codes(status):
    assert not is_retryable(http_error(status))


def test_403_rate_limit_is_retryable():
    old_style = {"error": {"message": "x", "errors": [{"reason": "rateLimitExceeded"}]}}
    both = {
        "error": {
            "message": "x",
            "errors": [{"reason": "userRateLimitExceeded"}],
            "details": [{"reason": "RATE_LIMIT_EXCEEDED"}],
        }
    }
    assert is_retryable(http_error(403, old_style))
    assert is_retryable(http_error(403, both))


def test_other_403_is_not_retryable():
    body = {
        "error": {"message": "x", "errors": [{"reason": "insufficientPermissions"}]}
    }
    assert not is_retryable(http_error(403, body))


def test_network_errors_are_retryable():
    assert is_retryable(ConnectionResetError())
    assert is_retryable(TimeoutError())
    assert not is_retryable(ValueError("bad"))


def test_unreadable_error_body_is_not_a_rate_limit():
    err = HttpError(httplib2.Response({"status": 403}), b"<html>Forbidden</html>")
    assert not is_retryable(err)


# --- messages for the counsellor ---


def test_describe_uses_googles_message():
    body = {"error": {"message": "Invalid To header"}}
    assert describe(http_error(400, body)) == "Google error 400: Invalid To header"


def test_describe_network_error():
    assert describe(TimeoutError()) == (
        "Couldn't reach Google (TimeoutError). Try again in a bit."
    )


def test_describe_refused_access():
    err = RefreshError("invalid_client: The OAuth client was not found.", {"raw": 1})
    assert describe(err) == (
        "Google refused the app's access: "
        "invalid_client: The OAuth client was not found."
    )


# --- the queue worker ---


@pytest.fixture
def worker_calls(monkeypatch) -> list[tuple[uuid.UUID, bool]]:
    """What the worker passed on to send_email (instead of sending)."""
    calls: list[tuple[uuid.UUID, bool]] = []
    monkeypatch.setattr(
        "app.services.queue._send",
        lambda email_id, last_try: calls.append((email_id, last_try)),
    )
    return calls


def test_worker_sends_the_email_in_the_job(worker_calls):
    email_id = uuid.uuid4()
    job = SendEmailWorker.new({"email_id": str(email_id)})  # type: ignore
    process_job(job)
    assert worker_calls == [(email_id, False)]


def test_worker_knows_its_last_try(worker_calls):
    job = SendEmailWorker.new({"email_id": str(uuid.uuid4())})  # type: ignore
    job.attempt = job.max_attempts
    process_job(job)
    assert worker_calls[0][1] is True


def test_worker_retry_delays():
    worker = SendEmailWorker()
    job = SendEmailWorker.new({"email_id": str(uuid.uuid4())})  # type: ignore
    delays = []
    for attempt in [1, 2, 3, 4]:
        job.attempt = attempt
        delays.append(worker.backoff(job))
    assert delays == [60, 300, 900, 900]
    assert RETRY_DELAYS == [60, 300, 900]


# --- the Gmail message ---


def test_redirected_outside_production():
    assert redirected("dmca@cf.test", "DMCA") == (
        "redirect@test.local",
        "[TEST → dmca@cf.test] DMCA",
    )


def test_not_redirected_in_production(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert redirected("dmca@cf.test", "DMCA") == ("dmca@cf.test", "DMCA")


def test_no_redirect_address_refuses_to_send(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_REDIRECT_TO", None)
    with pytest.raises(RuntimeError):
        redirected("dmca@cf.test", "DMCA")


def test_build_message():
    pdf = StoredFile(name="report.pdf", mime_type="application/pdf", data=b"%PDF")
    message: EmailMessage = build_message(
        OutgoingEmail(
            to="dmca@cf.test", subject="DMCA", body="Hello", attachments=[pdf]
        )
    )
    assert message["To"] == "redirect@test.local"
    assert message["Subject"] == "[TEST → dmca@cf.test] DMCA"
    assert message["Message-ID"]
    assert message["From"] is None
    body = message.get_body()
    assert body is not None and body.get_content().strip() == "Hello"
    [attachment] = list(message.iter_attachments())
    assert attachment.get_filename() == "report.pdf"
    assert attachment.get_content_type() == "application/pdf"
    assert attachment.get_content() == b"%PDF"


# --- settings ---


def test_settings_need_a_redirect_outside_production():
    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="staging", EMAIL_REDIRECT_TO=None)  # type: ignore[call-arg]


def test_settings_in_production_need_no_redirect():
    Settings(ENVIRONMENT="production", EMAIL_REDIRECT_TO=None)  # type: ignore[call-arg]
