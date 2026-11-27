"""Storing files in the connected Google account's Drive.

Everything goes into one folder (DRIVE_FOLDER_NAME), created the first time
it's needed, so the app's uploads don't spread across the Drive. The key is the
Drive file id; moving or renaming the file in Drive doesn't break anything.
"""

import io

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build  # type: ignore[import-untyped]
from googleapiclient.http import (  # type: ignore[import-untyped]
    MediaIoBaseDownload,
    MediaIoBaseUpload,
)

from app.core.config import settings
from app.services.storage.base import StoredFile

FOLDER_MIME = "application/vnd.google-apps.folder"


class DriveStorage:
    def __init__(self, creds: Credentials):
        self.files = build(
            "drive", "v3", credentials=creds, cache_discovery=False
        ).files()

    def _folder_id(self) -> str:
        """The app's folder, created if it doesn't exist yet.

        With the drive.file scope the app only sees files it made itself, so
        this can't pick up someone else's folder with the same name.
        """
        name = settings.DRIVE_FOLDER_NAME.replace("'", "\\'")
        found = self.files.list(
            q=f"name = '{name}' and mimeType = '{FOLDER_MIME}' and trashed = false",
            fields="files(id)",
            pageSize=1,
        ).execute()
        if found["files"]:
            return found["files"][0]["id"]
        created = self.files.create(
            body={"name": settings.DRIVE_FOLDER_NAME, "mimeType": FOLDER_MIME},
            fields="id",
        ).execute()
        return created["id"]

    def save(self, name: str, data: bytes, mime_type: str) -> str:
        media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime_type)
        created = self.files.create(
            body={"name": name, "parents": [self._folder_id()]},
            media_body=media,
            fields="id",
        ).execute()
        return created["id"]

    def get(self, key: str) -> StoredFile:
        meta = self.files.get(fileId=key, fields="name,mimeType").execute()
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, self.files.get_media(fileId=key))
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return StoredFile(
            name=meta["name"], mime_type=meta["mimeType"], data=buffer.getvalue()
        )
