"""Google connection API: connect the shared account, check it, disconnect.

Connecting and disconnecting are admin-only; anyone logged in can see the status
(the UI shows "Reconnect Google" when it's broken).
"""

from urllib.parse import urlencode

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.api.deps import AdminDep, CurrentUserDep, SessionDep
from app.core.config import settings
from app.crud.dmca.google_connection import (
    delete_connection,
    get_connection,
    save_connection,
)
from app.models import User, UserRole
from app.models.dmca.enums import GoogleConnectionStatus
from app.models.dmca.google_connection import GoogleConnectUrl, GoogleStatus
from app.services.google_auth import (
    GoogleConnectError,
    consent_url,
    exchange_code,
    read_state,
)

router = APIRouter(prefix="/google", tags=["dmca"])

# the frontend page the browser lands on after connecting
RETURN_PATH = "/dmca/config"


def _back_to_app(**params: str) -> RedirectResponse:
    return RedirectResponse(
        f"{settings.FRONTEND_HOST}{RETURN_PATH}?{urlencode(params)}"
    )


@router.get("/connect", response_model=GoogleConnectUrl)
def connect(current_user: AdminDep) -> GoogleConnectUrl:
    """The Google sign-in URL. The frontend sends the browser there."""
    assert current_user.id is not None
    return GoogleConnectUrl(url=consent_url(current_user.id))


@router.get("/callback")
def callback(
    session: SessionDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Where Google sends the browser back. Stores the token, then returns to
    the app with ?google=connected, or ?google=error&reason=...
    """
    if error or not code or not state:
        return _back_to_app(google="error", reason=error or "Sign-in was cancelled")

    user_id = read_state(state)
    user = session.get(User, user_id) if user_id is not None else None
    if user is None or user.role != UserRole.admin or not user.is_active:
        return _back_to_app(google="error", reason="The link expired, try again")

    try:
        tokens = exchange_code(code)
    except GoogleConnectError as err:
        return _back_to_app(google="error", reason=str(err))
    except Exception:
        return _back_to_app(google="error", reason="Google sign-in failed, try again")

    assert user.id is not None
    save_connection(
        session=session,
        account_email=tokens.account_email,
        refresh_token=tokens.refresh_token,
        scopes=tokens.scopes,
        connected_by=user.id,
    )
    return _back_to_app(google="connected")


@router.get("/status", response_model=GoogleStatus)
def status(session: SessionDep, _: CurrentUserDep) -> GoogleStatus:
    connection = get_connection(session=session)
    if connection is None:
        return GoogleStatus(connected=False)
    return GoogleStatus(
        connected=connection.status == GoogleConnectionStatus.connected,
        status=connection.status,
        account_email=connection.account_email,
        connected_at=connection.connected_at,
        last_error=connection.last_error,
    )


@router.delete("")
def disconnect(session: SessionDep, _: AdminDep) -> dict[str, str]:
    """Forget the stored token. Access can also be removed in the Google
    account's security settings."""
    delete_connection(session=session)
    return {"message": "Google disconnected"}
