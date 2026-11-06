"""Tests for app/services/template.py (no DB, plain functions)."""

import pytest

from app.models.dmca.enums import EmailType
from app.services.template import (
    MINOR_PARAGRAPH,
    AddressInput,
    GroundInput,
    LinkInput,
    build_subject,
    pick_address,
    render_body,
)

# --- subject ---


def test_subject_lists_up_to_three_domains():
    assert build_subject(["a.test"], False) == "DMCA Takedown Request – a.test"
    assert (
        build_subject(["a.test", "b.test", "c.test", "d.test", "e.test"], False)
        == "DMCA Takedown Request – a.test, b.test, c.test +2 more"
    )


def test_minor_subject_says_csam():
    assert build_subject(["a.test"], True) == "CSAM/DMCA Takedown Request – a.test"


# --- body ---


def body(**overrides) -> str:
    args = {
        "full_name": "Jane Doe",
        "recipient_name": "Cloudflare",
        "links": [LinkInput("https://a.test/1", "a.test")],
        "legal_grounds": [],
        "is_minor": False,
    }
    return render_body(**{**args, **overrides})


def test_body_has_name_recipient_and_link():
    text = body()
    assert text.startswith("Hi,\n\n")
    assert "Jane Doe is the exclusive rights holder" in text
    assert "following link:\nhttps://a.test/1" in text
    assert "for materials on a.test" in text
    assert "breaches Cloudflare's copyright infringement policy." in text


def test_body_groups_links_by_domain_when_several():
    text = body(
        links=[
            LinkInput("https://a.test/1", "a.test"),
            LinkInput("https://b.test/1", "b.test"),
            LinkInput("https://a.test/2", "a.test"),
        ]
    )
    assert "for materials on a.test, b.test" in text
    assert (
        "a.test:\n  https://a.test/1\n  https://a.test/2\nb.test:\n  https://b.test/1"
        in text
    )


def test_body_lists_legal_grounds():
    text = body(
        legal_grounds=[
            GroundInput("Section 66E", "Privacy."),
            GroundInput("Rule 3", "Intermediary duty."),
        ]
    )
    assert (
        "policy, along with the following:\n"
        "- Section 66E: Privacy.\n- Rule 3: Intermediary duty."
    ) in text


def test_minor_paragraph_only_for_minor_cases():
    assert MINOR_PARAGRAPH not in body(is_minor=False)
    text = body(is_minor=True)
    assert MINOR_PARAGRAPH in text
    # right after the paragraph about Indian law
    assert f"A cybercrime report has been filed.\n\n{MINOR_PARAGRAPH}" in text


# --- address ---

CF = [
    AddressInput("abuse@cf.test", EmailType.abuse),
    AddressInput("dmca@cf.test", EmailType.dmca),
    AddressInput("dmca2@cf.test", EmailType.dmca),
    AddressInput("hello@cf.test", EmailType.general),
]


def test_default_adult_prefers_dmca_and_first_address():
    assert pick_address(CF, is_minor=False, wanted=None) == (
        EmailType.dmca,
        "dmca@cf.test",
    )


def test_wanted_type_is_used():
    assert pick_address(CF, is_minor=False, wanted=EmailType.abuse) == (
        EmailType.abuse,
        "abuse@cf.test",
    )


def test_wanted_type_missing_raises():
    with pytest.raises(ValueError):
        pick_address(CF, is_minor=False, wanted=EmailType.csam)


def test_minor_prefers_csam_then_dmca():
    with_csam = [*CF, AddressInput("csam@cf.test", EmailType.csam)]
    assert pick_address(with_csam, is_minor=True, wanted=None) == (
        EmailType.csam,
        "csam@cf.test",
    )
    assert pick_address(CF, is_minor=True, wanted=None) == (
        EmailType.dmca,
        "dmca@cf.test",
    )


def test_falls_back_to_general():
    only_general = [AddressInput("hello@x.test", EmailType.general)]
    assert pick_address(only_general, is_minor=False, wanted=None) == (
        EmailType.general,
        "hello@x.test",
    )


def test_no_addresses_is_none():
    assert pick_address([], is_minor=False, wanted=None) is None
    # an adult case never uses a csam-only address by default
    only_csam = [AddressInput("csam@x.test", EmailType.csam)]
    assert pick_address(only_csam, is_minor=False, wanted=None) is None
