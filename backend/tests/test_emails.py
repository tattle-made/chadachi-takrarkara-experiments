"""Tests for the DMCA takedown emails API: creating drafts, editing, listing."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlmodel import Session, select

from app.models.dmca import CaseLink, EmailStatus, TakedownEmail
from app.services.template import MINOR_PARAGRAPH
from tests.conftest import auth_headers

BASE = "/api/v1/dmca"


@pytest.fixture
def admin(admin_token) -> dict[str, str]:
    return auth_headers(admin_token)


@pytest.fixture
def member(member_token) -> dict[str, str]:
    return auth_headers(member_token)


def post(client, headers, path, body) -> dict:
    response = client.post(f"{BASE}{path}", json=body, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def make_recipient(client, admin, name, emails, domains) -> str:
    """A recipient with {type: address} emails and {domain: relation} links."""
    recipient_id = post(client, admin, "/recipients", {"name": name})["id"]
    for email_type, address in emails.items():
        post(
            client,
            admin,
            f"/recipients/{recipient_id}/emails",
            {"address": address, "email_type": email_type},
        )
    for domain, relation in domains.items():
        post(
            client,
            admin,
            f"/recipients/{recipient_id}/domains",
            {"domain": domain, "relation": relation},
        )
    return recipient_id


def make_ground(client, admin, title, **flags) -> str:
    body = {"title": title, "citation": f"{title} cite", "clause_text": f"{title}."}
    return post(client, admin, "/legal-grounds", {**body, **flags})["id"]


@pytest.fixture
def setup(client, admin, member):
    """Two recipients, four legal grounds, and a case with four links."""
    ids = {
        "cf": make_recipient(
            client,
            admin,
            "Cloudflare",
            {"abuse": "abuse@cf.test", "dmca": "dmca@cf.test"},
            {"site-a.test": "cdn", "site-c.test": "cdn"},
        ),
        "host": make_recipient(
            client,
            admin,
            "Host Co",
            {"general": "hello@host.test"},
            {"site-b.test": "host"},
        ),
        "default": make_ground(client, admin, "Default", default_selected=True),
        "optional": make_ground(client, admin, "Optional"),
        "minor": make_ground(
            client, admin, "Minor", default_selected=True, minor_only=True
        ),
        "off": make_ground(client, admin, "Off", default_selected=True, active=False),
    }
    profile = post(client, member, "/profiles", {"full_name": "Jane Doe"})
    case = post(client, member, f"/profiles/{profile['id']}/cases", {"title": "March"})
    post(
        client,
        member,
        f"/cases/{case['id']}/links",
        {"text": "site-a.test/1 site-a.test/2 site-b.test/1 site-c.test/1"},
    )
    ids["profile"] = profile["id"]
    ids["case"] = case["id"]
    return ids


def drafts(client, headers, case_id, items):
    return client.post(
        f"{BASE}/cases/{case_id}/drafts", json={"items": items}, headers=headers
    )


def created(client, headers, case_id, items) -> list[dict]:
    """The new drafts from POST /drafts (fails the test on an error)."""
    response = drafts(client, headers, case_id, items)
    assert response.status_code == 200, response.text
    return response.json()["created"]


# --- creating drafts ---


def test_default_drafts(client, member, setup):
    response = drafts(
        client,
        member,
        setup["case"],
        [
            {"domain": "site-a.test", "recipient_id": setup["cf"], "relation": "cdn"},
            {
                "domain": "site-b.test",
                "recipient_id": setup["host"],
                "relation": "host",
            },
        ],
    )
    assert response.status_code == 200, response.text
    cf, host = response.json()["created"]

    assert cf["status"] == "draft"
    assert cf["recipient_name"] == "Cloudflare"
    assert cf["relation"] == "cdn"
    # no type picked: dmca comes first
    assert (cf["email_type"], cf["to_address"]) == ("dmca", "dmca@cf.test")
    assert [link["url"] for link in cf["links"]] == ["site-a.test/1", "site-a.test/2"]
    assert cf["subject"] == "DMCA Takedown Request – site-a.test"
    # only the active, default, non-minor ground
    assert [g["title"] for g in cf["legal_grounds"]] == ["Default"]
    assert "Jane Doe is the exclusive rights holder" in cf["body"]
    assert "site-a.test/2" in cf["body"]
    assert "- Default cite: Default." in cf["body"]
    assert cf["is_body_custom"] is False

    # Host Co only has a general address
    assert (host["email_type"], host["to_address"]) == ("general", "hello@host.test")


def test_dropdown_type_picks_that_address(client, member, setup):
    item = {"domain": "site-a.test", "recipient_id": setup["cf"], "email_type": "abuse"}
    (draft,) = created(client, member, setup["case"], [item])
    assert (draft["email_type"], draft["to_address"]) == ("abuse", "abuse@cf.test")


def test_type_the_recipient_lacks_is_400(client, member, setup):
    item = {"domain": "site-a.test", "recipient_id": setup["cf"], "email_type": "csam"}
    assert drafts(client, member, setup["case"], [item]).status_code == 400


def test_same_recipient_and_type_is_one_email(client, member, setup):
    items = [
        {"domain": "site-a.test", "recipient_id": setup["cf"]},
        {"domain": "site-c.test", "recipient_id": setup["cf"]},
    ]
    (draft,) = created(client, member, setup["case"], items)
    assert len(draft["links"]) == 3
    assert draft["subject"] == "DMCA Takedown Request – site-a.test, site-c.test"
    assert "site-a.test:\n  site-a.test/1" in draft["body"]


def test_same_recipient_different_types_is_two_emails(client, member, setup):
    items = [
        {"domain": "site-a.test", "recipient_id": setup["cf"], "email_type": "dmca"},
        {"domain": "site-c.test", "recipient_id": setup["cf"], "email_type": "abuse"},
    ]
    result = created(client, member, setup["case"], items)
    assert [d["to_address"] for d in result] == ["dmca@cf.test", "abuse@cf.test"]


def test_minor_case(client, member, setup):
    client.patch(
        f"{BASE}/cases/{setup['case']}", json={"is_minor": True}, headers=member
    )
    item = {"domain": "site-a.test", "recipient_id": setup["cf"]}
    (draft,) = created(client, member, setup["case"], [item])

    # Cloudflare has no csam address, so dmca is next
    assert draft["email_type"] == "dmca"
    assert draft["subject"].startswith("CSAM/DMCA Takedown Request")
    assert MINOR_PARAGRAPH in draft["body"]
    assert [g["title"] for g in draft["legal_grounds"]] == ["Default", "Minor"]


def test_removed_links_are_left_out(client, session: Session, member, setup):
    # mark one link removed directly in the DB
    link = session.exec(select(CaseLink).where(CaseLink.url == "site-a.test/1")).one()
    link.removed_at = datetime.now(timezone.utc)
    session.add(link)
    session.commit()

    item = {"domain": "site-a.test", "recipient_id": setup["cf"]}
    (draft,) = created(client, member, setup["case"], [item])
    assert [link["url"] for link in draft["links"]] == ["site-a.test/2"]


def test_domain_with_no_links_is_400(client, member, setup):
    item = {"domain": "nothing.test", "recipient_id": setup["cf"]}
    assert drafts(client, member, setup["case"], [item]).status_code == 400


def test_unknown_recipient_is_400(client, member, setup):
    item = {"domain": "site-a.test", "recipient_id": str(uuid.uuid4())}
    assert drafts(client, member, setup["case"], [item]).status_code == 400


def test_recipient_without_emails_gets_empty_address(client, admin, member, setup):
    bare = make_recipient(client, admin, "Bare", {}, {})
    item = {"domain": "site-a.test", "recipient_id": bare}
    (draft,) = created(client, member, setup["case"], [item])
    assert draft["to_address"] is None
    assert draft["email_type"] is None
    assert draft["relation"] is None


def test_unknown_case_is_404(client, member, setup):
    item = {"domain": "site-a.test", "recipient_id": setup["cf"]}
    assert drafts(client, member, uuid.uuid4(), [item]).status_code == 404


def test_empty_items_is_422(client, member, setup):
    assert drafts(client, member, setup["case"], []).status_code == 422


# --- editing ---


@pytest.fixture
def draft(client, member, setup) -> dict:
    item = {"domain": "site-a.test", "recipient_id": setup["cf"]}
    return created(client, member, setup["case"], [item])[0]


def patch(client, headers, email_id, body):
    return client.patch(f"{BASE}/emails/{email_id}", json=body, headers=headers)


def test_edit_subject_address_and_body(client, member, draft):
    response = patch(
        client,
        member,
        draft["id"],
        {"subject": "New", "to_address": "x@cf.test", "custom_body": "Hello"},
    )
    assert response.status_code == 200
    body = response.json()
    assert (body["subject"], body["to_address"], body["body"]) == (
        "New",
        "x@cf.test",
        "Hello",
    )
    assert body["is_body_custom"] is True

    # null goes back to the generated body
    reset = patch(client, member, draft["id"], {"custom_body": None}).json()
    assert reset["is_body_custom"] is False
    assert reset["body"].startswith("Hi,")
    assert reset["subject"] == "New"


def test_unchanged_body_sent_back_stays_generated(client, member, setup, draft):
    # the form sends the body untouched along with a subject change
    response = patch(
        client,
        member,
        draft["id"],
        {"subject": "New", "custom_body": draft["body"] + "\n"},
    )
    assert response.json()["is_body_custom"] is False

    # so ticking a ground still updates the body
    body = patch(
        client, member, draft["id"], {"legal_ground_ids": [setup["optional"]]}
    ).json()
    assert "- Optional cite: Optional." in body["body"]


def test_body_matching_new_grounds_stays_generated(client, member, setup, draft):
    # grounds changed and the body sent is what the template makes for them
    first = patch(
        client, member, draft["id"], {"legal_ground_ids": [setup["optional"]]}
    ).json()
    response = patch(
        client,
        member,
        draft["id"],
        {"legal_ground_ids": [setup["optional"]], "custom_body": first["body"]},
    )
    assert response.json()["is_body_custom"] is False


def test_edit_grounds_changes_generated_body(client, member, setup, draft):
    body = patch(
        client, member, draft["id"], {"legal_ground_ids": [setup["optional"]]}
    ).json()
    assert [g["title"] for g in body["legal_grounds"]] == ["Optional"]
    assert "- Optional cite: Optional." in body["body"]
    assert "Default cite" not in body["body"]


def test_edit_links(client, member, draft):
    keep = draft["links"][0]["id"]
    body = patch(client, member, draft["id"], {"link_ids": [keep]}).json()
    assert [link["id"] for link in body["links"]] == [keep]


def test_edit_with_link_from_other_case_is_400(client, member, setup, draft):
    other = post(
        client, member, f"/profiles/{setup['profile']}/cases", {"title": "Other"}
    )
    link = post(client, member, f"/cases/{other['id']}/links", {"text": "z.test/1"})
    response = patch(
        client, member, draft["id"], {"link_ids": [link["added"][0]["id"]]}
    )
    assert response.status_code == 400


def test_edit_with_no_links_is_400(client, member, draft):
    assert patch(client, member, draft["id"], {"link_ids": []}).status_code == 400


def set_status(session: Session, email_id: str, status: EmailStatus) -> None:
    email = session.get(TakedownEmail, uuid.UUID(email_id))
    email.status = status
    session.add(email)
    session.commit()


def test_cannot_edit_or_delete_once_sent(client, session: Session, member, draft):
    set_status(session, draft["id"], EmailStatus.sent)
    assert patch(client, member, draft["id"], {"subject": "x"}).status_code == 409
    url = f"{BASE}/emails/{draft['id']}"
    assert client.delete(url, headers=member).status_code == 409


def test_delete_draft(client, member, draft):
    url = f"{BASE}/emails/{draft['id']}"
    assert client.delete(url, headers=member).status_code == 200
    assert client.get(url, headers=member).status_code == 404


# --- sending links again, and adding to an existing draft ---


def add_link(client, member, case_id, url) -> None:
    post(client, member, f"/cases/{case_id}/links", {"text": url})


def test_links_already_emailed_can_be_sent_again(
    client, session: Session, member, setup, draft
):
    set_status(session, draft["id"], EmailStatus.sent)
    add_link(client, member, setup["case"], "site-a.test/3")
    item = {"domain": "site-a.test", "recipient_id": setup["cf"]}
    (second,) = created(client, member, setup["case"], [item])
    # all of the site's links that are still up, the sent ones too
    assert [link["url"] for link in second["links"]] == [
        "site-a.test/1",
        "site-a.test/2",
        "site-a.test/3",
    ]


def test_escalation_to_another_recipient_gets_the_same_links(
    client, member, setup, draft
):
    item = {"domain": "site-a.test", "recipient_id": setup["host"]}
    (escalation,) = created(client, member, setup["case"], [item])
    assert [link["url"] for link in escalation["links"]] == [
        "site-a.test/1",
        "site-a.test/2",
    ]


def test_add_to_existing_draft(client, member, setup, draft):
    add_link(client, member, setup["case"], "site-a.test/3")
    item = {
        "domain": "site-a.test",
        "recipient_id": setup["cf"],
        "add_to_email_id": draft["id"],
    }
    result = drafts(client, member, setup["case"], [item]).json()
    assert result["created"] == []
    (updated,) = result["updated"]
    assert updated["id"] == draft["id"]
    assert [link["url"] for link in updated["links"]] == [
        "site-a.test/1",
        "site-a.test/2",
        "site-a.test/3",
    ]
    assert "site-a.test/3" in updated["body"]


def test_add_to_draft_with_nothing_new_is_400(client, member, setup, draft):
    item = {
        "domain": "site-a.test",
        "recipient_id": setup["cf"],
        "add_to_email_id": draft["id"],
    }
    # the draft already has both site-a.test links
    assert drafts(client, member, setup["case"], [item]).status_code == 400


def test_add_to_edited_draft_resets_body(client, member, setup, draft):
    patch(client, member, draft["id"], {"custom_body": "Hand written"})
    add_link(client, member, setup["case"], "site-a.test/3")
    item = {
        "domain": "site-a.test",
        "recipient_id": setup["cf"],
        "add_to_email_id": draft["id"],
    }
    (updated,) = drafts(client, member, setup["case"], [item]).json()["updated"]
    assert updated["is_body_custom"] is False
    assert "site-a.test/3" in updated["body"]


def test_add_to_draft_updates_subject_unless_edited(client, member, setup, draft):
    item = {
        "domain": "site-c.test",
        "recipient_id": setup["cf"],
        "add_to_email_id": draft["id"],
    }
    (updated,) = drafts(client, member, setup["case"], [item]).json()["updated"]
    assert updated["subject"] == "DMCA Takedown Request – site-a.test, site-c.test"

    # a subject changed by hand is kept
    patch(client, member, draft["id"], {"subject": "My subject"})
    add_link(client, member, setup["case"], "site-c.test/2")
    (again,) = drafts(client, member, setup["case"], [item]).json()["updated"]
    assert again["subject"] == "My subject"


def test_add_to_draft_of_other_recipient_is_400(client, member, setup, draft):
    item = {
        "domain": "site-b.test",
        "recipient_id": setup["host"],
        "add_to_email_id": draft["id"],
    }
    assert drafts(client, member, setup["case"], [item]).status_code == 400


def test_add_to_sent_email_is_400(client, session: Session, member, setup, draft):
    set_status(session, draft["id"], EmailStatus.sent)
    add_link(client, member, setup["case"], "site-a.test/3")
    item = {
        "domain": "site-a.test",
        "recipient_id": setup["cf"],
        "add_to_email_id": draft["id"],
    }
    assert drafts(client, member, setup["case"], [item]).status_code == 400


# --- listing ---


def test_list_filters(client, session: Session, member, setup, draft):
    item = {"domain": "site-b.test", "recipient_id": setup["host"]}
    other = created(client, member, setup["case"], [item])[0]
    set_status(session, other["id"], EmailStatus.sent)

    everything = client.get(f"{BASE}/emails", headers=member).json()
    assert len(everything) == 2

    only_drafts = client.get(f"{BASE}/emails?status=draft", headers=member).json()
    assert [e["id"] for e in only_drafts] == [draft["id"]]

    other_case = client.get(f"{BASE}/emails?case_id={uuid.uuid4()}", headers=member)
    assert other_case.json() == []


# --- legal grounds: can't delete one an email uses ---


def test_cannot_delete_legal_ground_an_email_uses(client, admin, setup, draft):
    used = client.delete(f"{BASE}/legal-grounds/{setup['default']}", headers=admin)
    assert used.status_code == 409
    unused = client.delete(f"{BASE}/legal-grounds/{setup['optional']}", headers=admin)
    assert unused.status_code == 200


# --- documents on a draft ---


def upload_doc(client, member, profile_id, data=b"fake pdf") -> str:
    """Upload a document to the profile and return its id."""
    response = client.post(
        f"{BASE}/profiles/{profile_id}/attachments",
        data={"kind": "cyber_crime_report"},
        files={"file": ("report.pdf", data, "application/pdf")},
        headers=member,
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_new_draft_has_no_documents(draft):
    assert draft["attachments"] == []


def test_attach_and_detach_documents(client, member, setup, draft):
    doc_ids = [upload_doc(client, member, setup["profile"]) for _ in range(2)]
    response = patch(client, member, draft["id"], {"attachment_ids": doc_ids})
    assert response.status_code == 200, response.text
    assert {a["id"] for a in response.json()["attachments"]} == set(doc_ids)
    # documents aren't written into the body
    assert "report.pdf" not in response.json()["body"]

    response = patch(client, member, draft["id"], {"attachment_ids": []})
    assert response.json()["attachments"] == []


def test_document_of_another_profile_is_400(client, member, setup, draft):
    other = post(client, member, "/profiles", {"full_name": "Someone Else"})
    doc_id = upload_doc(client, member, other["id"])
    response = patch(client, member, draft["id"], {"attachment_ids": [doc_id]})
    assert response.status_code == 400


def test_unknown_document_is_400(client, member, draft):
    response = patch(
        client, member, draft["id"], {"attachment_ids": [str(uuid.uuid4())]}
    )
    assert response.status_code == 400


def test_documents_over_the_email_limit_are_400(
    client, member, setup, draft, monkeypatch
):
    from app.crud.dmca import takedown_email as crud

    doc_ids = [upload_doc(client, member, setup["profile"], b"123") for _ in range(2)]
    monkeypatch.setattr(crud, "MAX_ATTACHMENT_BYTES", 5)
    response = patch(client, member, draft["id"], {"attachment_ids": doc_ids})
    assert response.status_code == 400
    assert "too big for Gmail" in response.json()["detail"]
