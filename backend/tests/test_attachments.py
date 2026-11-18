"""Tests for the DMCA attachments API: uploading, listing and downloading a
profile's documents. Files go to the in-memory storage (STORAGE_BACKEND=memory)."""

import uuid

import pytest

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


def test_needs_login(client, profile_id):
    assert upload(client, {}, profile_id).status_code == 401
