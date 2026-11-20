"""Tests for the DMCA Config API: recipients, their emails, domain links, resolve."""

import uuid

import pytest
from sqlmodel import Session, select

from app.models.dmca import Domain, DomainRecipient, RecipientEmail
from tests.conftest import auth_headers

BASE = "/api/v1/dmca"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def admin(admin_token) -> dict[str, str]:
    return auth_headers(admin_token)


@pytest.fixture
def member(member_token) -> dict[str, str]:
    return auth_headers(member_token)


def make_recipient(client, headers, name="Cloudflare") -> str:
    """Create a recipient through the API and return its id."""
    response = client.post(f"{BASE}/recipients", json={"name": name}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["id"]


def add_email(
    client, headers, recipient_id, address="abuse@cdn.test", email_type="abuse"
):
    return client.post(
        f"{BASE}/recipients/{recipient_id}/emails",
        json={"address": address, "email_type": email_type},
        headers=headers,
    )


def add_domain(client, headers, recipient_id, domain="example-site.com", rel="cdn"):
    return client.post(
        f"{BASE}/recipients/{recipient_id}/domains",
        json={"domain": domain, "relation": rel},
        headers=headers,
    )


# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------


def test_list_requires_login(client):
    assert client.get(f"{BASE}/recipients").status_code == 401


def test_member_cannot_create(client, member):
    response = client.post(f"{BASE}/recipients", json={"name": "X"}, headers=member)
    assert response.status_code == 403


def test_member_can_read(client, admin, member):
    recipient_id = make_recipient(client, admin)
    assert client.get(f"{BASE}/recipients", headers=member).status_code == 200
    response = client.get(f"{BASE}/recipients/{recipient_id}", headers=member)
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# recipients
# ---------------------------------------------------------------------------


def test_create_and_list(client, admin):
    make_recipient(client, admin, "Cloudflare")
    make_recipient(client, admin, "Example Host")

    body = client.get(f"{BASE}/recipients", headers=admin).json()
    assert body["count"] == 2
    assert {r["name"] for r in body["data"]} == {"Cloudflare", "Example Host"}


def test_get_unknown_recipient_is_404(client, admin):
    response = client.get(f"{BASE}/recipients/{uuid.uuid4()}", headers=admin)
    assert response.status_code == 404


def test_get_with_bad_uuid_is_422(client, admin):
    response = client.get(f"{BASE}/recipients/not-a-uuid", headers=admin)
    assert response.status_code == 422


def test_patch_changes_only_sent_fields(client, admin):
    recipient_id = make_recipient(client, admin, "Cloudflare")
    response = client.patch(
        f"{BASE}/recipients/{recipient_id}", json={"notes": "slow"}, headers=admin
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Cloudflare"
    assert response.json()["notes"] == "slow"


def test_delete_recipient_removes_its_emails_and_links(client, session: Session, admin):
    recipient_id = make_recipient(client, admin)
    add_email(client, admin, recipient_id)
    add_domain(client, admin, recipient_id)

    assert (
        client.delete(f"{BASE}/recipients/{recipient_id}", headers=admin).status_code
        == 200
    )
    assert (
        client.get(f"{BASE}/recipients/{recipient_id}", headers=admin).status_code
        == 404
    )
    assert session.exec(select(RecipientEmail)).all() == []
    assert session.exec(select(DomainRecipient)).all() == []
    # the domain itself stays, other recipients may use it
    assert len(session.exec(select(Domain)).all()) == 1


# ---------------------------------------------------------------------------
# emails
# ---------------------------------------------------------------------------


def test_add_email_is_lowercased(client, admin):
    recipient_id = make_recipient(client, admin)
    response = add_email(client, admin, recipient_id, address="  Abuse@CDN.test ")
    assert response.status_code == 200
    assert response.json()["address"] == "abuse@cdn.test"


def test_duplicate_email_in_other_case_is_409(client, admin):
    recipient_id = make_recipient(client, admin)
    add_email(client, admin, recipient_id, address="abuse@cdn.test")
    response = add_email(client, admin, recipient_id, address="ABUSE@cdn.test")
    assert response.status_code == 409


def test_same_email_under_another_recipient_is_409(client, admin):
    first = make_recipient(client, admin, "First")
    second = make_recipient(client, admin, "Second")
    add_email(client, admin, first)
    assert add_email(client, admin, second).status_code == 409


def test_same_address_with_another_type_is_ok(client, admin):
    recipient_id = make_recipient(client, admin)
    add_email(client, admin, recipient_id, email_type="abuse")
    assert add_email(client, admin, recipient_id, email_type="dmca").status_code == 200


def test_add_email_to_unknown_recipient_is_404(client, admin):
    assert add_email(client, admin, uuid.uuid4()).status_code == 404


def test_delete_email(client, admin):
    recipient_id = make_recipient(client, admin)
    email_id = add_email(client, admin, recipient_id).json()["id"]

    url = f"{BASE}/recipients/{recipient_id}/emails/{email_id}"
    assert client.delete(url, headers=admin).status_code == 200
    body = client.get(f"{BASE}/recipients/{recipient_id}", headers=admin).json()
    assert body["emails"] == []


def test_delete_email_through_other_recipient_is_404(client, admin):
    owner = make_recipient(client, admin, "Owner")
    other = make_recipient(client, admin, "Other")
    email_id = add_email(client, admin, owner).json()["id"]

    url = f"{BASE}/recipients/{other}/emails/{email_id}"
    assert client.delete(url, headers=admin).status_code == 404


# ---------------------------------------------------------------------------
# domain links
# ---------------------------------------------------------------------------


def test_add_domain_link(client, admin):
    recipient_id = make_recipient(client, admin)
    response = add_domain(client, admin, recipient_id, domain="Example-Site.com")
    assert response.status_code == 200
    assert response.json()["relation"] == "cdn"
    assert response.json()["domain"]["domain"] == "example-site.com"


def test_same_domain_is_reused(client, session: Session, admin):
    first = make_recipient(client, admin, "Cloudflare")
    second = make_recipient(client, admin, "Example Host")
    add_domain(client, admin, first, rel="cdn")
    add_domain(client, admin, second, domain="EXAMPLE-SITE.com", rel="host")
    assert len(session.exec(select(Domain)).all()) == 1


def test_duplicate_domain_link_is_409(client, admin):
    recipient_id = make_recipient(client, admin)
    add_domain(client, admin, recipient_id, rel="cdn")
    assert add_domain(client, admin, recipient_id, rel="cdn").status_code == 409


def test_same_domain_with_another_relation_is_ok(client, admin):
    recipient_id = make_recipient(client, admin)
    add_domain(client, admin, recipient_id, rel="cdn")
    assert add_domain(client, admin, recipient_id, rel="host").status_code == 200


def test_delete_domain_link_keeps_domain(client, session: Session, admin):
    recipient_id = make_recipient(client, admin)
    link_id = add_domain(client, admin, recipient_id).json()["id"]

    url = f"{BASE}/recipients/{recipient_id}/domains/{link_id}"
    assert client.delete(url, headers=admin).status_code == 200
    assert session.exec(select(DomainRecipient)).all() == []
    assert len(session.exec(select(Domain)).all()) == 1


def test_delete_domain_link_through_other_recipient_is_404(client, admin):
    owner = make_recipient(client, admin, "Owner")
    other = make_recipient(client, admin, "Other")
    link_id = add_domain(client, admin, owner).json()["id"]

    url = f"{BASE}/recipients/{other}/domains/{link_id}"
    assert client.delete(url, headers=admin).status_code == 404


# ---------------------------------------------------------------------------
# resolve
# ---------------------------------------------------------------------------


def test_resolve_known_and_unknown_domains(client, admin, member):
    recipient_id = make_recipient(client, admin, "Cloudflare")
    add_domain(client, admin, recipient_id, domain="example-site.com", rel="cdn")

    response = client.get(
        f"{BASE}/domains/resolve?domains=Example-Site.com,unknown.test", headers=member
    )
    assert response.status_code == 200
    known, unknown = response.json()

    assert known["domain"] == "example-site.com"
    assert known["recipient_links"][0]["relation"] == "cdn"
    assert known["recipient_links"][0]["recipient"]["name"] == "Cloudflare"
    assert unknown == {"domain": "unknown.test", "recipient_links": []}


def test_resolve_lists_recipient_email_types(client, admin, member):
    recipient_id = make_recipient(client, admin, "Cloudflare")
    # added out of order and with two addresses of one type, to check the
    # result is unique and in EmailType order
    add_email(client, admin, recipient_id, address="abuse@cdn.test", email_type="abuse")
    add_email(client, admin, recipient_id, address="dmca@cdn.test", email_type="dmca")
    add_email(client, admin, recipient_id, address="dmca2@cdn.test", email_type="dmca")
    add_domain(client, admin, recipient_id)

    response = client.get(
        f"{BASE}/domains/resolve?domains=example-site.com", headers=member
    )
    recipient = response.json()[0]["recipient_links"][0]["recipient"]
    assert recipient["email_types"] == ["dmca", "abuse"]
    # the addresses themselves aren't sent
    assert "emails" not in recipient


def test_resolve_recipient_without_emails_has_no_types(client, admin, member):
    recipient_id = make_recipient(client, admin)
    add_domain(client, admin, recipient_id)
    response = client.get(
        f"{BASE}/domains/resolve?domains=example-site.com", headers=member
    )
    assert response.json()[0]["recipient_links"][0]["recipient"]["email_types"] == []


def test_resolve_drops_blanks_and_duplicates(client, member):
    response = client.get(
        f"{BASE}/domains/resolve?domains=a.test, ,A.test,b.test", headers=member
    )
    assert [d["domain"] for d in response.json()] == ["a.test", "b.test"]


def test_resolve_needs_domains_param(client, member):
    assert client.get(f"{BASE}/domains/resolve", headers=member).status_code == 422
