"""Where attachment files are stored. Use get_storage(); it picks the backend
from the STORAGE_BACKEND setting."""

from sqlmodel import Session

from app.core.config import settings
from app.services.google_auth import get_credentials
from app.services.storage.base import Storage, StoredFile
from app.services.storage.drive import DriveStorage
from app.services.storage.memory import MemoryStorage

__all__ = ["Storage", "StoredFile", "get_storage", "memory_storage"]

# one shared instance, so files saved in one request can be read in the next
memory_storage = MemoryStorage()


def get_storage(*, session: Session) -> Storage:
    """The configured storage. For Drive, raises GoogleNotConnected if Google
    isn't connected."""
    if settings.STORAGE_BACKEND == "memory":
        return memory_storage
    return DriveStorage(get_credentials(session=session))
