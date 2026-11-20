"""Tests for the DMCA attachments API: uploading, listing and downloading a
profile's documents. Files go to the in-memory storage (STORAGE_BACKEND=memory)."""

import json
import uuid

import httplib2  # type: ignore[import-untyped]
import pytest
from googleapiclient.errors import HttpError  # type: ignore[import-untyped]

from app.api.routes.dmca import attachments as attachments_route
from app.core.config import settings
from tests.conftest import auth_headers

BASE = "/api/v1/dmca"


@pytest.fixture
def member(member_token) -> dict[str, str]:
    """Auth headers for a counsellor."""
    return auth_headers(member_token)


@pytest.fixture
def profile_id(client, member) -> str:
    """A new profile to upload to."""
    response = client.post(
        f"{BASE}/profiles", json={"full_name": "Jane Doe"}, headers=member
    )
    return response.json()["id"]


def upload(
    client,
    headers,
    profile_id,
    *,
    kind="government_id",
    name="id.pdf",
    data=b"%PDF-1.4 fake",
    mime="application/pdf",
):
    """POST a multipart upload, like the browser's file input would."""
    return client.post(
        f"{BASE}/profiles/{profile_id}/attachments",
        data={"kind": kind},
        files={"file": (name, data, mime)},
        headers=headers,
    )


def test_upload_list_and_download(client, member, profile_id):
    response = upload(client, member, profile_id)
    assert response.status_code == 200, response.text
    doc = response.json()
    assert doc["kind"] == "government_id"
    assert doc["file_name"] == "id.pdf"
    assert doc["mime_type"] == "application/pdf"
    assert doc["size"] == len(b"%PDF-1.4 fake")
    assert "storage_key" not in doc

    listed = client.get(f"{BASE}/profiles/{profile_id}/attachments", headers=member)
    assert [d["id"] for d in listed.json()] == [doc["id"]]

    file = client.get(f"{BASE}/attachments/{doc['id']}/file", headers=member)
    assert file.status_code == 200
    assert file.content == b"%PDF-1.4 fake"
    assert file.headers["content-type"] == "application/pdf"
    assert "id.pdf" in file.headers["content-disposition"]


def test_list_is_newest_first(client, member, profile_id):
    first = upload(client, member, profile_id, name="a.pdf").json()
    second = upload(client, member, profile_id, name="b.pdf").json()
    listed = client.get(f"{BASE}/profiles/{profile_id}/attachments", headers=member)
    assert [d["id"] for d in listed.json()] == [second["id"], first["id"]]


def test_non_english_file_name_downloads(client, member, profile_id):
    doc = upload(client, member, profile_id, name="पहचान.pdf").json()
    assert doc["file_name"] == "पहचान.pdf"
    file = client.get(f"{BASE}/attachments/{doc['id']}/file", headers=member)
    assert file.status_code == 200


def test_empty_file_is_400(client, member, profile_id):
    assert upload(client, member, profile_id, data=b"").status_code == 400


def test_too_big_file_is_413(client, member, profile_id, monkeypatch):
    monkeypatch.setattr(attachments_route, "MAX_ATTACHMENT_BYTES", 5)
    assert upload(client, member, profile_id, data=b"123456").status_code == 413
    assert upload(client, member, profile_id, data=b"12345").status_code == 200


def test_unknown_kind_is_422(client, member, profile_id):
    assert upload(client, member, profile_id, kind="selfie").status_code == 422


def test_unknown_profile_is_404(client, member):
    assert upload(client, member, uuid.uuid4()).status_code == 404
    listed = client.get(f"{BASE}/profiles/{uuid.uuid4()}/attachments", headers=member)
    assert listed.status_code == 404


def test_unknown_document_is_404(client, member):
    response = client.get(f"{BASE}/attachments/{uuid.uuid4()}/file", headers=member)
    assert response.status_code == 404


def test_google_not_connected_is_409(client, member, profile_id, monkeypatch):
    # Drive storage with no Google connection saved
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "drive")
    response = upload(client, member, profile_id)
    assert response.status_code == 409
    assert "Config" in response.json()["detail"]


class BrokenDrive:
    """Storage whose every call fails the way Drive would."""

    def __init__(self, error: Exception) -> None:
        self.error = error

    def save(self, name, data, mime_type):
        raise self.error

    def get(self, key):
        raise self.error


def broken_drive(monkeypatch, error: Exception) -> None:
    monkeypatch.setattr(
        attachments_route, "get_storage", lambda session: BrokenDrive(error)
    )


def drive_404() -> HttpError:
    body = json.dumps({"error": {"message": "File not found: abc"}}).encode()
    return HttpError(httplib2.Response({"status": 404}), body)


def test_drive_error_on_upload_is_502_with_googles_message(
    client, member, profile_id, monkeypatch
):
    broken_drive(monkeypatch, drive_404())
    response = upload(client, member, profile_id)
    assert response.status_code == 502
    assert response.json()["detail"] == (
        "Couldn't upload the file to Drive: Google error 404: File not found: abc"
    )


def test_drive_error_on_download_is_502(client, member, profile_id, monkeypatch):
    doc_id = upload(client, member, profile_id).json()["id"]
    broken_drive(monkeypatch, TimeoutError())
    response = client.get(f"{BASE}/attachments/{doc_id}/file", headers=member)
    assert response.status_code == 502
    assert "Couldn't reach Google" in response.json()["detail"]


def test_our_own_bug_is_not_shown_as_a_google_error(
    client, member, profile_id, monkeypatch
):
    broken_drive(monkeypatch, KeyError("oops"))
    with pytest.raises(KeyError):
        upload(client, member, profile_id)


def test_needs_login(client, profile_id):
    assert upload(client, {}, profile_id).status_code == 401
