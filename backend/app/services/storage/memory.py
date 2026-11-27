"""Keeps files in memory, for tests (STORAGE_BACKEND=memory). Lost on restart."""

import uuid

from app.services.storage.base import StoredFile


class MemoryStorage:
    def __init__(self) -> None:
        self.files: dict[str, StoredFile] = {}

    def save(self, name: str, data: bytes, mime_type: str) -> str:
        key = str(uuid.uuid4())
        self.files[key] = StoredFile(name=name, mime_type=mime_type, data=data)
        return key

    def get(self, key: str) -> StoredFile:
        """Raises KeyError for an unknown key."""
        return self.files[key]
