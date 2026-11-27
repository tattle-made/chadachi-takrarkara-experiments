"""Tests for the DMCA profiles API."""

import uuid

import pytest

from tests.conftest import auth_headers

URL = "/api/v1/dmca/profiles"


@pytest.fixture
def member(member_token) -> dict[str, str]:
    return auth_headers(member_token)


def make_profile(client, headers, **body) -> dict:
    """Create a profile through the API and return the response body."""
    response = client.post(URL, json={"full_name": "Jane Doe", **body}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_requires_login(client):
    assert client.get(URL).status_code == 401


def test_member_can_create(client, member):
    profile = make_profile(client, member, display_name="JD-1", notes="met in March")
    assert profile["full_name"] == "Jane Doe"
    assert profile["display_name"] == "JD-1"
    assert profile["cases"] == []


def test_names_are_trimmed_and_blank_display_name_is_none(client, member):
    profile = make_profile(client, member, full_name="  Jane Doe ", display_name="  ")
    assert profile["full_name"] == "Jane Doe"
    assert profile["display_name"] is None


def test_full_name_is_required(client, member):
    assert client.post(URL, json={"full_name": ""}, headers=member).status_code == 422
    assert client.post(URL, json={}, headers=member).status_code == 422


def test_list_newest_first(client, member):
    make_profile(client, member, full_name="First")
    make_profile(client, member, full_name="Second")
    body = client.get(URL, headers=member).json()
    assert body["count"] == 2
    assert [p["full_name"] for p in body["data"]] == ["Second", "First"]
    assert body["data"][0]["created_at"]


def test_search_matches_both_names_ignoring_case(client, member):
    make_profile(client, member, full_name="Jane Doe", display_name="JD-Delhi")
    make_profile(client, member, full_name="Mary Major")

    by_full = client.get(f"{URL}?q=jane", headers=member).json()
    assert [p["full_name"] for p in by_full["data"]] == ["Jane Doe"]

    by_display = client.get(f"{URL}?q=delhi", headers=member).json()
    assert [p["full_name"] for p in by_display["data"]] == ["Jane Doe"]


def test_get_includes_cases(client, member):
    profile = make_profile(client, member)
    client.post(f"{URL}/{profile['id']}/cases", json={"title": "March"}, headers=member)

    body = client.get(f"{URL}/{profile['id']}", headers=member).json()
    assert [c["title"] for c in body["cases"]] == ["March"]


def test_get_unknown_is_404(client, member):
    assert client.get(f"{URL}/{uuid.uuid4()}", headers=member).status_code == 404


def test_patch_changes_only_sent_fields(client, member):
    profile = make_profile(client, member, display_name="JD-1")
    response = client.patch(
        f"{URL}/{profile['id']}", json={"notes": "new"}, headers=member
    )
    assert response.status_code == 200
    assert response.json()["display_name"] == "JD-1"
    assert response.json()["notes"] == "new"


def test_patch_blank_display_name_clears_it(client, member):
    profile = make_profile(client, member, display_name="JD-1")
    response = client.patch(
        f"{URL}/{profile['id']}", json={"display_name": ""}, headers=member
    )
    assert response.json()["display_name"] is None
