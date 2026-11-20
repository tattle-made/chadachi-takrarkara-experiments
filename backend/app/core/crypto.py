"""Encrypting secrets stored in the DB (e.g. the Google refresh token).

Uses Fernet with TOKEN_ENCRYPTION_KEY. Make a key with:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
Changing the key makes stored secrets unreadable (Google then has to be reconnected).
"""

from cryptography.fernet import Fernet

from app.core.config import settings


def _fernet() -> Fernet:
    return Fernet(settings.TOKEN_ENCRYPTION_KEY)


def encrypt(text: str) -> str:
    return _fernet().encrypt(text.encode()).decode()


def decrypt(token: str) -> str:
    """Raises cryptography.fernet.InvalidToken if the key changed or the text was altered."""
    return _fernet().decrypt(token.encode()).decode()
