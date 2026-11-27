"""What every storage backend must offer, so the rest of the app doesn't care
where files live (Drive today; S3 or a disk could be swapped in later)."""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class StoredFile:
    name: str
    mime_type: str
    data: bytes


class Storage(Protocol):
    def save(self, name: str, data: bytes, mime_type: str) -> str:
        """Store a file and return its key, used later to fetch it."""
        ...

    def get(self, key: str) -> StoredFile:
        """Fetch a file by the key save() returned."""
        ...
