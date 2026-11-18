"""Tests for after an email is sent: marking "Got a reply", the "No reply · 48h+"
flag, and Escalate's suggestion of who to email next.

The sites and recipients (as in Config):

    site    admin    CDN         host    registrar
    a.com   A-Admin  Cloudflare  HostCo  GoDaddy
    b.com   -        Cloudflare  -       Namecheap
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import Session

from app.models.dmca import EmailStatus, TakedownEmail
from tests.conftest import auth_headers
from tests.test_emails import BASE, created, make_recipient, post


@pytest.fixture
def member(member_token) -> dict[str, str]:
    return auth_headers(member_token)


@pytest.fixture
def admin(admin_token) -> dict[str, str]:
    return auth_headers(admin_token)


@pytest.fixture
def ids(client, admin, member) -> dict[str, str]:
    """The recipients above, and a case with one link on each site."""

    def recipient(name, domains):
        return make_recipient(
            client, admin, name, {"dmca": f"dmca@{name}.test"}, domains
        )

    ids = {
        "admin": recipient("A-Admin", {"a.com": "website_owner"}),
        "cf": recipient("Cloudflare", {"a.com": "cdn", "b.com": "cdn"}),
        "host": recipient("HostCo", {"a.com": "host"}),
        "godaddy": recipient("GoDaddy", {"a.com": "registrar"}),
        "namecheap": recipient("Namecheap", {"b.com": "registrar"}),
        "other": recipient("Someone Else", {}),
    }
    profile = post(client, member, "/profiles", {"full_name": "Jane Doe"})
    case = post(client, member, f"/profiles/{profile['id']}/cases", {"title": "June"})
    post(client, member, f"/cases/{case['id']}/links", {"text": "a.com/1 b.com/1"})
    ids["case"] = case["id"]
    return ids


def sent_email(client, session: Session, member, ids, rows, hours_ago=1) -> dict:
    """Draft one email from review-screen rows, then fake that it was sent."""
    [draft] = created(client, member, ids["case"], rows)
    email = session.get(TakedownEmail, uuid.UUID(draft["id"]))
    assert email is not None
    email.status = EmailStatus.sent
    email.sent_at = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    session.add(email)
    session.commit()
    return draft


def row(ids, domain, who, relation=None) -> dict:
    item = {"domain": domain, "recipient_id": ids[who]}
    return {**item, "relation": relation} if relation else item


def get_email(client, member, email_id) -> dict:
    response = client.get(f"{BASE}/emails/{email_id}", headers=member)
    assert response.status_code == 200, response.text
    return response.json()


def mark(client, member, email_id, received: bool):
    return client.put(
        f"{BASE}/emails/{email_id}/reply-received",
        json={"received": received},
        headers=member,
    )


def suggestions(client, member, email_id) -> dict[str, str | None]:
    """{site: suggested recipient name} from GET /escalation."""
    response = client.get(f"{BASE}/emails/{email_id}/escalation", headers=member)
    assert response.status_code == 200, response.text
    return {s["domain"]: s["recipient_name"] for s in response.json()}


# --- "Got a reply" ---


def test_mark_and_unmark_reply(client, session: Session, member, ids):
    email = sent_email(
        client, session, member, ids, [row(ids, "a.com", "admin", "website_owner")]
    )
    response = mark(client, member, email["id"], True)
    assert response.status_code == 200, response.text
    assert response.json()["reply_received_at"] is not None

    response = mark(client, member, email["id"], False)
    assert response.json()["reply_received_at"] is None


def test_cannot_mark_reply_on_a_draft(client, member, ids):
    [draft] = created(client, member, ids["case"], [row(ids, "a.com", "admin")])
    response = mark(client, member, draft["id"], True)
    assert response.status_code == 409
    assert "A-Admin" in response.json()["detail"]


def test_unknown_email_is_404(client, member):
    assert mark(client, member, uuid.uuid4(), True).status_code == 404


# --- "No reply · 48h+" ---


def test_no_reply_after_48_hours(client, session: Session, member, ids):
    old = sent_email(client, session, member, ids, [row(ids, "a.com", "admin")], 49)
    recent = sent_email(client, session, member, ids, [row(ids, "b.com", "cf")], 47)
    assert get_email(client, member, old["id"])["no_reply_48h"] is True
    assert get_email(client, member, recent["id"])["no_reply_48h"] is False


def test_a_reply_clears_no_reply(client, session: Session, member, ids):
    email = sent_email(client, session, member, ids, [row(ids, "a.com", "admin")], 49)
    mark(client, member, email["id"], True)
    assert get_email(client, member, email["id"])["no_reply_48h"] is False


def test_drafts_are_never_no_reply(client, member, ids):
    [draft] = created(client, member, ids["case"], [row(ids, "a.com", "admin")])
    assert draft["no_reply_48h"] is False


def test_no_reply_filter(client, session: Session, member, ids):
    old = sent_email(client, session, member, ids, [row(ids, "a.com", "admin")], 49)
    replied = sent_email(client, session, member, ids, [row(ids, "a.com", "cf")], 49)
    mark(client, member, replied["id"], True)
    sent_email(client, session, member, ids, [row(ids, "b.com", "cf")], 1)
    created(client, member, ids["case"], [row(ids, "a.com", "host")])  # a draft

    response = client.get(
        f"{BASE}/emails", params={"no_reply_48h": "true"}, headers=member
    )
    assert [e["id"] for e in response.json()] == [old["id"]]


# --- Escalate: who to email next ---


def test_admin_escalates_to_cloudflare(client, session: Session, member, ids):
    email = sent_email(
        client, session, member, ids, [row(ids, "a.com", "admin", "website_owner")]
    )
    assert suggestions(client, member, email["id"]) == {"a.com": "Cloudflare"}


def test_cloudflare_escalates_to_host(client, session: Session, member, ids):
    email = sent_email(client, session, member, ids, [row(ids, "a.com", "cf", "cdn")])
    assert suggestions(client, member, email["id"]) == {"a.com": "HostCo"}


def test_missing_step_is_skipped(client, session: Session, member, ids):
    # b.com has no host, so after Cloudflare comes its registrar
    email = sent_email(client, session, member, ids, [row(ids, "b.com", "cf", "cdn")])
    assert suggestions(client, member, email["id"]) == {"b.com": "Namecheap"}


def test_nothing_after_the_registrar(client, session: Session, member, ids):
    email = sent_email(
        client, session, member, ids, [row(ids, "a.com", "godaddy", "registrar")]
    )
    response = client.get(f"{BASE}/emails/{email['id']}/escalation", headers=member)
    assert response.json() == [
        {
            "domain": "a.com",
            "recipient_id": None,
            "recipient_name": None,
            "relation": None,
        }
    ]


def test_one_email_for_two_sites_gets_a_suggestion_per_site(
    client, session: Session, member, ids
):
    email = sent_email(
        client,
        session,
        member,
        ids,
        [row(ids, "a.com", "cf", "cdn"), row(ids, "b.com", "cf", "cdn")],
    )
    assert suggestions(client, member, email["id"]) == {
        "a.com": "HostCo",
        "b.com": "Namecheap",
    }


def test_step_comes_from_the_recipients_role_for_the_site(
    client, session: Session, member, ids
):
    # picked by hand (no relation sent), but Cloudflare is a.com's CDN
    email = sent_email(client, session, member, ids, [row(ids, "a.com", "cf")])
    assert suggestions(client, member, email["id"]) == {"a.com": "HostCo"}


def test_unknown_step_starts_from_the_beginning(client, session: Session, member, ids):
    # someone not linked to a.com: the chain starts at a.com's admin
    email = sent_email(client, session, member, ids, [row(ids, "a.com", "other")])
    assert suggestions(client, member, email["id"]) == {"a.com": "A-Admin"}


def test_suggestion_includes_the_role(client, session: Session, member, ids):
    email = sent_email(
        client, session, member, ids, [row(ids, "a.com", "admin", "website_owner")]
    )
    response = client.get(f"{BASE}/emails/{email['id']}/escalation", headers=member)
    assert response.json() == [
        {
            "domain": "a.com",
            "recipient_id": ids["cf"],
            "recipient_name": "Cloudflare",
            "relation": "cdn",
        }
    ]


def test_escalate_works_after_a_reply(client, session: Session, member, ids):
    email = sent_email(client, session, member, ids, [row(ids, "a.com", "admin")])
    mark(client, member, email["id"], True)
    assert suggestions(client, member, email["id"]) == {"a.com": "Cloudflare"}


def test_cannot_escalate_a_draft(client, member, ids):
    [draft] = created(client, member, ids["case"], [row(ids, "a.com", "admin")])
    response = client.get(f"{BASE}/emails/{draft['id']}/escalation", headers=member)
    assert response.status_code == 409
