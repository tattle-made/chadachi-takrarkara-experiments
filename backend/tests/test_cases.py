"""Tests for the DMCA cases API: creating, listing, assigning, and adding links."""

import uuid

import pytest
from sqlmodel import Session

from tests.conftest import auth_headers, make_user

BASE = "/api/v1/dmca"


@pytest.fixture
def admin(admin_token) -> dict[str, str]:
    return auth_headers(admin_token)


@pytest.fixture
def member(member_token) -> dict[str, str]:
    return auth_headers(member_token)


def make_case(client, headers, **body) -> dict:
    """Create a profile and a case under it; return the case."""
    profile = client.post(
        f"{BASE}/profiles", json={"full_name": "Jane Doe"}, headers=headers
    ).json()
    response = client.post(
        f"{BASE}/profiles/{profile['id']}/cases",
        json={"title": "March", **body},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def add_links(client, headers, case_id, text):
    return client.post(
        f"{BASE}/cases/{case_id}/links", json={"text": text}, headers=headers
    )


# --- creating and reading ---


def test_requires_login(client):
    assert client.get(f"{BASE}/cases").status_code == 401


def test_create_case(client, member):
    case = make_case(client, member, is_minor=True)
    assert case["title"] == "March"
    assert case["is_minor"] is True
    assert case["assignee"] is None
    assert case["profile"]["full_name"] == "Jane Doe"
    assert case["links"] == []


def test_create_case_for_unknown_profile_is_404(client, member):
    response = client.post(
        f"{BASE}/profiles/{uuid.uuid4()}/cases", json={"title": "x"}, headers=member
    )
    assert response.status_code == 404


def test_get_unknown_case_is_404(client, member):
    assert client.get(f"{BASE}/cases/{uuid.uuid4()}", headers=member).status_code == 404


# --- assigning ---


def test_create_assigned_case(client, member, member_user):
    case = make_case(client, member, assigned_to=member_user.id)
    assert case["assignee"] == {"id": member_user.id, "email": member_user.email}


def test_assign_to_unknown_user_is_400(client, member):
    profile = client.post(
        f"{BASE}/profiles", json={"full_name": "Jane"}, headers=member
    ).json()
    response = client.post(
        f"{BASE}/profiles/{profile['id']}/cases",
        json={"title": "x", "assigned_to": 9999},
        headers=member,
    )
    assert response.status_code == 400


def test_assign_to_archived_user_is_400(client, session: Session, member):
    archived = make_user(session, "old@test.com", is_active=False)
    case = make_case(client, member)
    response = client.patch(
        f"{BASE}/cases/{case['id']}", json={"assigned_to": archived.id}, headers=member
    )
    assert response.status_code == 400


def test_patch_assign_and_unassign(client, member, member_user):
    case = make_case(client, member)
    url = f"{BASE}/cases/{case['id']}"

    assigned = client.patch(url, json={"assigned_to": member_user.id}, headers=member)
    assert assigned.json()["assignee"]["id"] == member_user.id

    # other fields untouched, and null unassigns
    unassigned = client.patch(url, json={"assigned_to": None}, headers=member)
    assert unassigned.json()["assignee"] is None
    assert unassigned.json()["title"] == "March"


def test_assigned_to_me_filter(client, admin, member, member_user, admin_user):
    make_case(client, admin, title="Mine", assigned_to=member_user.id)
    make_case(client, admin, title="Theirs", assigned_to=admin_user.id)
    make_case(client, admin, title="Nobody")

    everything = client.get(f"{BASE}/cases", headers=member).json()
    assert everything["count"] == 3

    mine = client.get(f"{BASE}/cases?assigned_to_me=true", headers=member).json()
    assert [c["title"] for c in mine["data"]] == ["Mine"]


def test_filter_by_profile(client, member):
    first = make_case(client, member, title="A")
    make_case(client, member, title="B")
    profile_id = first["profile"]["id"]
    body = client.get(f"{BASE}/cases?profile_id={profile_id}", headers=member).json()
    assert [c["title"] for c in body["data"]] == ["A"]


def test_assignees_lists_active_users(client, session: Session, member, admin_user):
    make_user(session, "old@test.com", is_active=False)
    emails = [
        u["email"] for u in client.get(f"{BASE}/assignees", headers=member).json()
    ]
    assert "admin@test.com" in emails
    assert "member@test.com" in emails
    assert "old@test.com" not in emails


# --- links ---


def test_add_links(client, member):
    case = make_case(client, member)
    response = add_links(
        client,
        member,
        case["id"],
        "https://www.Example-Site.com/a\nexample-site.com/b, not-a-link",
    )
    assert response.status_code == 200
    body = response.json()
    assert [(link["url"], link["domain"]) for link in body["added"]] == [
        ("https://www.Example-Site.com/a", "example-site.com"),
        ("example-site.com/b", "example-site.com"),
    ]
    assert body["skipped"] == []
    assert body["invalid"] == ["not-a-link"]
    assert body["added"][0]["removed_at"] is None

    links = client.get(f"{BASE}/cases/{case['id']}", headers=member).json()["links"]
    assert len(links) == 2


def test_add_links_skips_ones_already_in_case(client, member):
    case = make_case(client, member)
    add_links(client, member, case["id"], "a.test/1")
    body = add_links(client, member, case["id"], "a.test/1 a.test/2 a.test/2").json()
    assert [link["url"] for link in body["added"]] == ["a.test/2"]
    assert body["skipped"] == ["a.test/1"]


def test_same_link_in_two_cases_is_fine(client, member):
    first = make_case(client, member)
    second = make_case(client, member)
    add_links(client, member, first["id"], "a.test/1")
    body = add_links(client, member, second["id"], "a.test/1").json()
    assert len(body["added"]) == 1


def test_add_links_needs_text(client, member):
    case = make_case(client, member)
    assert add_links(client, member, case["id"], "").status_code == 422


def test_add_links_to_unknown_case_is_404(client, member):
    assert add_links(client, member, uuid.uuid4(), "a.test/1").status_code == 404


def test_delete_link(client, member):
    case = make_case(client, member)
    link_id = add_links(client, member, case["id"], "a.test/1").json()["added"][0]["id"]

    url = f"{BASE}/cases/{case['id']}/links/{link_id}"
    assert client.delete(url, headers=member).status_code == 200
    assert (
        client.get(f"{BASE}/cases/{case['id']}", headers=member).json()["links"] == []
    )


def test_delete_link_through_other_case_is_404(client, member):
    owner = make_case(client, member)
    other = make_case(client, member)
    link_id = add_links(client, member, owner["id"], "a.test/1").json()["added"][0][
        "id"
    ]

    url = f"{BASE}/cases/{other['id']}/links/{link_id}"
    assert client.delete(url, headers=member).status_code == 404
