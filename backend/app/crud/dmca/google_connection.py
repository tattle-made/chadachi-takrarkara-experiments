"""DB functions for the Google connection (there's at most one row)."""

from sqlmodel import Session, delete, select

from app.core.crypto import encrypt
from app.models.dmca.enums import GoogleConnectionStatus
from app.models.dmca.google_connection import GoogleConnection


def get_connection(*, session: Session) -> GoogleConnection | None:
    return session.exec(select(GoogleConnection)).first()


def save_connection(
    *,
    session: Session,
    account_email: str,
    refresh_token: str,
    scopes: list[str],
    connected_by: int,
) -> GoogleConnection:
    """Store a new connection, replacing any old one. The token is encrypted."""
    session.exec(delete(GoogleConnection))  # type: ignore[call-overload]
    connection = GoogleConnection(
        account_email=account_email,
        refresh_token_encrypted=encrypt(refresh_token),
        scopes=" ".join(scopes),
        connected_by=connected_by,
    )
    session.add(connection)
    session.commit()
    session.refresh(connection)
    return connection


def mark_broken(*, session: Session, connection: GoogleConnection, error: str) -> None:
    connection.status = GoogleConnectionStatus.broken
    connection.last_error = error
    session.add(connection)
    session.commit()


def delete_connection(*, session: Session) -> None:
    session.exec(delete(GoogleConnection))  # type: ignore[call-overload]
    session.commit()
