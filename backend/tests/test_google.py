"""Tests for the Google connection: connect, callback, status, credentials.

Google itself is never called: the code exchange and token refresh are mocked.
"""

import time
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import jwt
import pytest
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import Flow
from sqlmodel import Session, select

from app.core.crypto import decrypt, encrypt
from app.models.dmca import GoogleConnection, GoogleConnectionStatus
from app.services import google_auth
from app.services.google_auth import (
    GoogleConnectError,
    GoogleNotConnected,
    GoogleTokens,
    get_credentials,
    make_state,
)
from tests.conftest import auth_headers

BASE = "/api/v1/google"
TOKENS = GoogleTokens(
    account_email="team@example.org",
    refresh_token="refresh-123",
    scopes=[google_auth.GMAIL_SEND, google_auth.DRIVE_FILE],
)


@pytest.fixture
def admin(admin_token) -> dict[str, str]:
    return auth_headers(admin_token)


@pytest.fixture
def member(member_token) -> dict[str, str]:
    return auth_headers(member_token)


def callback(client, **params):
    response = client.get(f"{BASE}/callback", params=params, follow_redirects=False)
    assert response.status_code == 307
    location = urlsplit(response.headers["location"])
    assert location.path == "/dmca/config"
    return parse_qs(location.query)


def connect(client, session, user, tokens=TOKENS):
    """Run the callback as if Google returned these tokens."""
    with patch("app.api.routes.dmca.google.exchange_code", return_value=tokens):
        return callback(client, code="abc", state=make_state(user.id))


def test_encrypt_round_trip():
    secret = encrypt("refresh-123")
    assert secret != "refresh-123"
    assert decrypt(secret) == "refresh-123"


def test_connect_url(client, admin):
    response = client.get(f"{BASE}/connect", headers=admin)
    assert response.status_code == 200
    url = urlsplit(response.json()["url"])
    query = parse_qs(url.query)
    assert url.netloc == "accounts.google.com"
    assert query["access_type"] == ["offline"]
    assert query["prompt"] == ["consent"]
    assert google_auth.GMAIL_SEND in query["scope"][0]
    assert query["state"]


def test_connect_is_admin_only(client, member):
    assert client.get(f"{BASE}/connect", headers=member).status_code == 403


def test_callback_stores_encrypted_token(client, session: Session, admin, admin_user):
    assert connect(client, session, admin_user) == {"google": ["connected"]}

    stored = session.exec(select(GoogleConnection)).one()
    assert stored.account_email == "team@example.org"
    assert stored.refresh_token_encrypted != "refresh-123"
    assert decrypt(stored.refresh_token_encrypted) == "refresh-123"
    assert stored.connected_by == admin_user.id

    status = client.get(f"{BASE}/status", headers=admin).json()
    assert status["connected"] is True
    assert status["account_email"] == "team@example.org"


def test_reconnect_replaces_old_connection(client, session: Session, admin_user):
    connect(client, session, admin_user)
    other = GoogleTokens("other@example.org", "refresh-456", TOKENS.scopes)
    connect(client, session, admin_user, other)
    (stored,) = session.exec(select(GoogleConnection)).all()
    assert stored.account_email == "other@example.org"


def test_callback_with_bad_state_stores_nothing(client, session: Session):
    params = callback(client, code="abc", state="not-a-real-state")
    assert params["google"] == ["error"]
    assert session.exec(select(GoogleConnection)).first() is None


def test_callback_state_from_member_is_rejected(client, session: Session, member_user):
    with patch("app.api.routes.dmca.google.exchange_code", return_value=TOKENS):
        params = callback(client, code="abc", state=make_state(member_user.id))
    assert params["google"] == ["error"]
    assert session.exec(select(GoogleConnection)).first() is None


def test_callback_when_user_cancels(client):
    params = callback(client, error="access_denied")
    assert params == {"google": ["error"], "reason": ["access_denied"]}


def test_callback_with_missing_scope(client, admin_user):
    with patch(
        "app.api.routes.dmca.google.exchange_code",
        side_effect=GoogleConnectError("Allow both Gmail and Drive access"),
    ):
        params = callback(client, code="abc", state=make_state(admin_user.id))
    assert params["reason"] == ["Allow both Gmail and Drive access"]


def test_status_when_never_connected(client, member):
    assert client.get(f"{BASE}/status", headers=member).json()["connected"] is False


def test_disconnect(client, session: Session, admin, member, admin_user):
    connect(client, session, admin_user)
    assert client.delete(BASE, headers=member).status_code == 403
    assert client.delete(BASE, headers=admin).status_code == 200
    assert session.exec(select(GoogleConnection)).first() is None


def test_get_credentials_without_connection(session: Session):
    with pytest.raises(GoogleNotConnected):
        get_credentials(session=session)


def test_get_credentials_refreshes(client, session: Session, admin_user):
    connect(client, session, admin_user)
    with patch("google.oauth2.credentials.Credentials.refresh") as refresh:
        creds = get_credentials(session=session)
    refresh.assert_called_once()
    assert creds.refresh_token == "refresh-123"


def test_revoked_token_marks_connection_broken(
    client, session: Session, admin, admin_user
):
    connect(client, session, admin_user)
    with patch(
        "google.oauth2.credentials.Credentials.refresh",
        side_effect=RefreshError("invalid_grant: Token has been expired or revoked."),
    ):
        with pytest.raises(GoogleNotConnected):
            get_credentials(session=session)

    stored = session.exec(select(GoogleConnection)).one()
    assert stored.status == GoogleConnectionStatus.broken
    status = client.get(f"{BASE}/status", headers=admin).json()
    assert status["connected"] is False
    assert status["status"] == "broken"

    # broken stays broken until someone reconnects
    with pytest.raises(GoogleNotConnected):
        get_credentials(session=session)


def fake_fetch_token(scope: str):
    """Stand-in for Flow.fetch_token: puts Google's token response on the session."""
    id_token = jwt.encode({"email": "team@example.org"}, "x", algorithm="HS256")

    def fetch(self, **kwargs):
        self.oauth2session.token = {
            "access_token": "access-1",
            "refresh_token": "refresh-123",
            "id_token": id_token,
            "scope": scope,
            "token_type": "Bearer",
            "expires_at": time.time() + 3600,
        }

    return fetch


def test_exchange_code_reads_google_response():
    scope = f"openid {google_auth.GMAIL_SEND} {google_auth.DRIVE_FILE}"
    with patch.object(Flow, "fetch_token", fake_fetch_token(scope)):
        tokens = google_auth.exchange_code("abc")
    assert tokens.account_email == "team@example.org"
    assert tokens.refresh_token == "refresh-123"


def test_exchange_code_needs_gmail_and_drive():
    # the admin unticked Drive on Google's screen
    scope = f"openid {google_auth.GMAIL_SEND}"
    with patch.object(Flow, "fetch_token", fake_fetch_token(scope)):
        with pytest.raises(GoogleConnectError):
            google_auth.exchange_code("abc")
