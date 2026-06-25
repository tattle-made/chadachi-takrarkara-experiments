import uuid
from unittest.mock import MagicMock, patch

from sqlmodel import Session

from tests.conftest import auth_headers, make_conversation, make_message, make_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_openai_response(text: str = "Draft email content") -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.output_text = text
    mock_resp.usage.input_tokens = 100
    mock_resp.usage.output_tokens = 200
    return mock_resp


# ---------------------------------------------------------------------------
# POST /email/generate
# ---------------------------------------------------------------------------


def test_generate_email_success(client, member_user, member_token):
    mock_resp = _mock_openai_response("Dear Platform,\n\nWe write to request...")

    with patch("app.api.routes.email._openai") as mock_openai:
        mock_openai.responses.create.return_value = mock_resp

        response = client.post(
            "/api/v1/email/generate",
            headers=auth_headers(member_token),
            json={"case_details": "Victim was harassed via repeated messages."},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "Dear Platform,\n\nWe write to request..."
    assert "conversation_id" in body
    assert "message_id" in body


def test_generate_email_unauthenticated(client):
    response = client.post(
        "/api/v1/email/generate",
        json={"case_details": "Some case details."},
    )
    assert response.status_code == 401


def test_generate_email_openai_failure_returns_502(client, member_token):
    with patch("app.api.routes.email._openai") as mock_openai:
        mock_openai.responses.create.side_effect = RuntimeError("OpenAI down")

        response = client.post(
            "/api/v1/email/generate",
            headers=auth_headers(member_token),
            json={"case_details": "Case details here."},
        )

    assert response.status_code == 502
    assert response.json()["detail"] == "Failed to generate email"


def test_generate_email_records_conversation_and_messages(
    client, session: Session, member_user, member_token
):
    from app.models import Conversation, Message

    mock_resp = _mock_openai_response("Generated email")

    with patch("app.api.routes.email._openai") as mock_openai:
        mock_openai.responses.create.return_value = mock_resp
        response = client.post(
            "/api/v1/email/generate",
            headers=auth_headers(member_token),
            json={"case_details": "Detailed case info."},
        )

    assert response.status_code == 200
    conv_id = response.json()["conversation_id"]
    msg_id = response.json()["message_id"]

    # Two messages should exist: user_query + llm_response
    from sqlmodel import select
    from app.models import MessageKind

    messages = session.exec(
        select(Message).where(Message.conversation_id == uuid.UUID(conv_id))
    ).all()
    assert len(messages) == 2
    kinds = {m.kind for m in messages}
    assert MessageKind.user_query in kinds
    assert MessageKind.llm_response in kinds


# ---------------------------------------------------------------------------
# GET /email/feedback/export
# ---------------------------------------------------------------------------


def test_export_feedback_csv_as_admin_empty(client, admin_token):
    response = client.get(
        "/api/v1/email/feedback/export", headers=auth_headers(admin_token)
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    lines = response.text.strip().split("\n")
    # Only header row when no feedback exists
    assert len(lines) == 1
    assert "feedback_id" in lines[0]


def test_export_feedback_csv_as_member_forbidden(client, member_token):
    response = client.get(
        "/api/v1/email/feedback/export", headers=auth_headers(member_token)
    )
    assert response.status_code == 403


def test_export_feedback_csv_as_manager_forbidden(client, manager_token):
    response = client.get(
        "/api/v1/email/feedback/export", headers=auth_headers(manager_token)
    )
    assert response.status_code == 403


def test_export_feedback_csv_unauthenticated(client):
    response = client.get("/api/v1/email/feedback/export")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /email/feedback
# ---------------------------------------------------------------------------


def test_submit_feedback_success(client, session: Session, member_user, member_token):
    conv = make_conversation(session, member_user)
    msg = make_message(session, conv, member_user, body="Email content to annotate")

    response = client.post(
        "/api/v1/email/feedback",
        headers=auth_headers(member_token),
        json={
            "message_id": str(msg.id),
            "annotations": [
                {
                    "start": 0,
                    "end": 5,
                    "text": "Email",
                    "tag": "hallucination",
                }
            ],
            "custom_comment": "This part looks wrong",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "feedback_id" in body


def test_submit_feedback_no_annotations(
    client, session: Session, member_user, member_token
):
    conv = make_conversation(session, member_user)
    msg = make_message(session, conv, member_user)

    response = client.post(
        "/api/v1/email/feedback",
        headers=auth_headers(member_token),
        json={
            "message_id": str(msg.id),
            "annotations": [],
        },
    )
    assert response.status_code == 200
    assert "feedback_id" in response.json()


def test_submit_feedback_message_not_found(client, member_token):
    response = client.post(
        "/api/v1/email/feedback",
        headers=auth_headers(member_token),
        json={
            "message_id": str(uuid.uuid4()),
            "annotations": [],
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Message not found"


def test_submit_feedback_not_owner(
    client, session: Session, admin_user, admin_token, member_user, member_token
):
    # Conversation belongs to member, admin tries to submit feedback
    conv = make_conversation(session, member_user)
    msg = make_message(session, conv, member_user)

    response = client.post(
        "/api/v1/email/feedback",
        headers=auth_headers(admin_token),
        json={
            "message_id": str(msg.id),
            "annotations": [],
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorised"


def test_submit_feedback_invalid_tag(
    client, session: Session, member_user, member_token
):
    conv = make_conversation(session, member_user)
    msg = make_message(session, conv, member_user)

    response = client.post(
        "/api/v1/email/feedback",
        headers=auth_headers(member_token),
        json={
            "message_id": str(msg.id),
            "annotations": [
                {
                    "start": 0,
                    "end": 5,
                    "text": "Email",
                    "tag": "not-a-real-tag",
                }
            ],
        },
    )
    assert response.status_code == 422


def test_submit_feedback_unauthenticated(client, session: Session, member_user):
    conv = make_conversation(session, member_user)
    msg = make_message(session, conv, member_user)

    response = client.post(
        "/api/v1/email/feedback",
        json={"message_id": str(msg.id), "annotations": []},
    )
    assert response.status_code == 401


def test_export_feedback_csv_with_data(
    client, session: Session, admin_user, admin_token, member_user, member_token
):
    conv = make_conversation(session, member_user)
    msg = make_message(session, conv, member_user, body="Sample email text here")

    client.post(
        "/api/v1/email/feedback",
        headers=auth_headers(member_token),
        json={
            "message_id": str(msg.id),
            "annotations": [
                {"start": 0, "end": 6, "text": "Sample", "tag": "too-verbose"}
            ],
            "custom_comment": "Too long",
        },
    )

    response = client.get(
        "/api/v1/email/feedback/export", headers=auth_headers(admin_token)
    )
    assert response.status_code == 200
    lines = response.text.strip().split("\n")
    assert len(lines) == 2  # header + 1 data row
    assert "too-verbose" in response.text
