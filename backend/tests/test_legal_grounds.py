"""Tests for the DMCA legal grounds API."""

import uuid

import pytest

from tests.conftest import auth_headers

URL = "/api/v1/dmca/legal-grounds"


@pytest.fixture
def admin(admin_token) -> dict[str, str]:
    return auth_headers(admin_token)


@pytest.fixture
def member(member_token) -> dict[str, str]:
    return auth_headers(member_token)


def make_ground(client, headers, **overrides) -> dict:
    """Create a legal ground through the API and return the response body."""
    body = {
        "title": "Privacy violation",
        "citation": "Section 66E, IT Act 2000",
        "clause_text": "The content violates the privacy of the person shown.",
        **overrides,
    }
    response = client.post(URL, json=body, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


# --- auth ---


def test_list_requires_login(client):
    assert client.get(URL).status_code == 401


def test_member_cannot_create(client, member):
    response = client.post(
        URL, json={"title": "x", "citation": "y", "clause_text": "z"}, headers=member
    )
    assert response.status_code == 403


def test_member_cannot_update(client, admin, member):
    ground = make_ground(client, admin)
    response = client.patch(
        f"{URL}/{ground['id']}", json={"active": False}, headers=member
    )
    assert response.status_code == 403


# --- create / list ---


def test_create_uses_defaults(client, admin):
    ground = make_ground(client, admin)
    assert ground["default_selected"] is False
    assert ground["minor_only"] is False
    assert ground["active"] is True


def test_create_rejects_empty_title(client, admin):
    response = client.post(
        URL, json={"title": "", "citation": "y", "clause_text": "z"}, headers=admin
    )
    assert response.status_code == 422


def test_list_returns_in_creation_order(client, admin, member):
    make_ground(client, admin, title="First")
    make_ground(client, admin, title="Second", minor_only=True)

    body = client.get(URL, headers=member).json()
    assert body["count"] == 2
    assert [g["title"] for g in body["data"]] == ["First", "Second"]


def test_list_hides_inactive_by_default(client, admin, member):
    make_ground(client, admin, title="On")
    make_ground(client, admin, title="Off", active=False)

    default = client.get(URL, headers=member).json()
    assert [g["title"] for g in default["data"]] == ["On"]

    everything = client.get(f"{URL}?include_inactive=true", headers=admin).json()
    assert {g["title"] for g in everything["data"]} == {"On", "Off"}


# --- update ---


def test_patch_turns_ground_off(client, admin, member):
    ground = make_ground(client, admin)
    response = client.patch(
        f"{URL}/{ground['id']}", json={"active": False}, headers=admin
    )
    assert response.status_code == 200
    assert response.json()["active"] is False
    # other fields untouched
    assert response.json()["title"] == ground["title"]
    assert client.get(URL, headers=member).json()["count"] == 0


def test_patch_unknown_ground_is_404(client, admin):
    response = client.patch(
        f"{URL}/{uuid.uuid4()}", json={"active": False}, headers=admin
    )
    assert response.status_code == 404


# --- delete ---


def test_delete_unused_ground(client, admin):
    ground = make_ground(client, admin)
    response = client.delete(f"{URL}/{ground['id']}", headers=admin)
    assert response.status_code == 200
    everything = client.get(f"{URL}?include_inactive=true", headers=admin).json()
    assert everything["count"] == 0


def test_delete_unknown_ground_is_404(client, admin):
    assert client.delete(f"{URL}/{uuid.uuid4()}", headers=admin).status_code == 404


def test_member_cannot_delete(client, admin, member):
    ground = make_ground(client, admin)
    assert client.delete(f"{URL}/{ground['id']}", headers=member).status_code == 403


# deleting a ground an email uses (409) is tested in test_emails.py, since it
# needs a case and a draft
