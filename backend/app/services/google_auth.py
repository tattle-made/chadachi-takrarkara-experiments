"""Connecting the shared Google account, and getting working credentials for it.

The flow: an admin opens consent_url(), signs in to Google and allows access.
Google sends the browser to our callback with a code; exchange_code() swaps it
for a refresh token, which the callback route stores (encrypted). Later,
get_credentials() turns that refresh token into a fresh access token for each
Gmail / Drive call.
"""

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow  # type: ignore[import-untyped]
from sqlmodel import Session

from app.core.config import settings
from app.core.crypto import decrypt
from app.core.security import ALGORITHM
from app.crud.dmca.google_connection import get_connection, mark_broken
from app.models.dmca.enums import GoogleConnectionStatus

# Google may return the scopes in a different order or with extras; without this
# the token exchange fails with "Scope has changed"
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

GMAIL_SEND = "https://www.googleapis.com/auth/gmail.send"
# only the files this app uploads, not the rest of the Drive
DRIVE_FILE = "https://www.googleapis.com/auth/drive.file"
# openid + email: so we know which account was connected
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    GMAIL_SEND,
    DRIVE_FILE,
]
REQUIRED_SCOPES = {GMAIL_SEND, DRIVE_FILE}

AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
# how long the admin has to finish the Google sign-in
STATE_TTL = timedelta(minutes=10)


class GoogleNotConnected(Exception):
    """No working Google connection: an admin has to connect (or reconnect) it."""


class GoogleConnectError(Exception):
    """Connecting failed, e.g. a box was unticked on Google's consent screen."""


@dataclass
class GoogleTokens:
    account_email: str
    refresh_token: str
    scopes: list[str]


def _flow() -> Flow:
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": AUTH_URI,
            "token_uri": TOKEN_URI,
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }
    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        # a server-side client has a secret, so PKCE isn't needed (and the
        # verifier would have to survive the round trip to Google)
        autogenerate_code_verifier=False,
    )


# --- connecting ---


def make_state(user_id: int) -> str:
    """A signed, short-lived token saying which admin started connecting.

    Google sends it back to the callback unchanged. The callback has no login
    header (it's a browser redirect), so this is how it knows who it is, and
    that the request really started here.
    """
    payload = {
        "sub": str(user_id),
        "type": "google_connect",
        "exp": datetime.now(timezone.utc) + STATE_TTL,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def read_state(state: str) -> int | None:
    """The user id from make_state(), or None if it's invalid or expired."""
    try:
        payload = jwt.decode(state, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError:
        return None
    if payload.get("type") != "google_connect":
        return None
    return int(payload["sub"])


def consent_url(user_id: int) -> str:
    """The Google page where the admin signs in and allows access."""
    url, _ = _flow().authorization_url(
        # offline + consent: always get a refresh token, even on a reconnect
        access_type="offline",
        prompt="consent",
        state=make_state(user_id),
    )
    return url


def exchange_code(code: str) -> GoogleTokens:
    """Swap the code from the callback for the account's refresh token."""
    flow = _flow()
    flow.fetch_token(code=code)
    creds = flow.credentials

    granted = flow.oauth2session.token.get("scope", [])
    if isinstance(granted, str):
        granted = granted.split()
    if not REQUIRED_SCOPES <= set(granted):
        raise GoogleConnectError("Allow both Gmail and Drive access on Google's screen")
    if not creds.refresh_token:
        raise GoogleConnectError("Google didn't return a refresh token")

    # the id token comes straight from Google's token endpoint (over HTTPS), so
    # it's only read here, not verified again
    claims = jwt.decode(creds.id_token, options={"verify_signature": False})
    return GoogleTokens(
        account_email=claims.get("email", ""),
        refresh_token=creds.refresh_token,
        scopes=list(granted),
    )


# --- using the connection ---


def get_credentials(*, session: Session) -> Credentials:
    """Working credentials for Gmail / Drive calls.

    Raises GoogleNotConnected if there's no connection, or Google refuses the
    token (revoked, expired): the connection is then marked broken.
    Network errors are raised as they are, so the caller can retry later.
    """
    connection = get_connection(session=session)
    if connection is None or connection.status != GoogleConnectionStatus.connected:
        raise GoogleNotConnected("Google isn't connected")

    creds = Credentials(
        token=None,
        refresh_token=decrypt(connection.refresh_token_encrypted),
        token_uri=TOKEN_URI,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=connection.scopes.split(),
    )
    try:
        creds.refresh(Request())
    except RefreshError as err:
        if "invalid_grant" in str(err):
            mark_broken(session=session, connection=connection, error=str(err))
            raise GoogleNotConnected("Google access was revoked or expired") from err
        raise
    return creds
