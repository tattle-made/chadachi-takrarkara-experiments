"""Tests for the PII guard used by POST /email/generate.

The focus is Presidio's Indian PAN recognizer, which ships a "PAN (Low)" pattern that
matches *any* 10-character token containing a letter and 4 digits at a score of 0.01.
PIIRemover never passes its threshold down to analyze(), so Presidio's default cutoff of
0 keeps those matches and ordinary tokens like "CASE123456" were redacted as <IN_PAN>.
app.api.routes.email swaps that recognizer for one without the offending pattern, and
switches context matching to whole-word so "company" no longer counts as "pan".

These tests assert on the redacted output rather than the pii_was_found flag wherever
PAN behaviour is under test, so that unrelated detections (spaCy tagging a bare token as
PERSON, for instance) cannot mask a PAN regression.
"""

import pytest

from app.api.routes.email import _get_pii_guard, check_pii

# Tokens that are not PANs but which the removed "PAN (Low)" pattern used to match.
NON_PAN_TOKENS = [
    "CASE123456",  # 5th char is a digit
    "REF20240099",
    "WFLOW77812",  # 5 letters then 5 digits
    "ESCQ9021X7",
    "ORDER12345",
    "TKT2024ABCD",  # 11 chars
    "2024-11-05",  # date, matched by PAN (Low) via the \w and - character class
]

# Structurally valid PANs: 5 letters (4th from the holder-type set ABCFGHJLPT),
# 4 digits, 1 letter.
PAN_TOKENS = [
    "ABCPE1234F",
    "AAAPL1234C",
    "BNZAA2318J",
    "AFZPK7190K",
]


# ---------------------------------------------------------------------------
# PAN false positives
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("token", NON_PAN_TOKENS)
def test_non_pan_tokens_are_not_redacted_as_pan(token):
    safe_text, _ = check_pii(f"Our internal reference for this matter is {token} today.")
    assert "<IN_PAN>" not in safe_text
    assert token in safe_text


def test_reference_id_alone_does_not_trigger_the_guard():
    text = (
        "The complainant approached our team through the helpline. Our internal "
        "reference for this matter is CASE123456, and the takedown request was given "
        "ticket TKT2024ABCD under workflow run WFLOW77812."
    )
    safe_text, pii_was_found = check_pii(text)
    assert pii_was_found is False
    assert safe_text == text


# ---------------------------------------------------------------------------
# Context enhancer: substring matching used to boost neighbours of "com-pan-y"
# ---------------------------------------------------------------------------


def test_company_does_not_boost_neighbouring_tokens():
    """"company" contains "pan"; under substring matching it boosted nearby scores."""
    text = "The company shared reference CASE123456 with us."
    safe_text, pii_was_found = check_pii(text)
    assert pii_was_found is False
    assert safe_text == text


def test_nearby_pan_keyword_does_not_redact_unrelated_tokens():
    """The literal word "PAN" is a context word; it must not sweep up neighbours."""
    text = "His PAN is ABCPE1234F and the case number is CASE123456."
    safe_text, pii_was_found = check_pii(text)
    assert pii_was_found is True
    assert safe_text == "His PAN is <IN_PAN> and the case number is CASE123456."


# ---------------------------------------------------------------------------
# PAN true positives - the fix must not disable PAN detection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("token", PAN_TOKENS)
def test_valid_pans_are_still_redacted(token):
    safe_text, pii_was_found = check_pii(f"The number on the card was {token} exactly.")
    assert pii_was_found is True
    assert "<IN_PAN>" in safe_text
    assert token not in safe_text


def test_pan_redacted_without_any_context_word_present():
    """PAN (High) scores 0.5 on its own, so detection must not depend on context."""
    safe_text, pii_was_found = check_pii("She later shared ABCPE1234F with the caller.")
    assert pii_was_found is True
    assert "<IN_PAN>" in safe_text


# ---------------------------------------------------------------------------
# Other entity types must be unaffected by the patch
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,placeholder",
    [
        ("Contact the victim at +91 99999 99999 please.", "<PHONE_NUMBER>"),
        ("Write to jane.doe@example.com for details.", "<EMAIL_ADDRESS>"),
        ("The complainant resides in Mumbai currently.", "<LOCATION>"),
    ],
)
def test_other_entities_still_detected(text, placeholder):
    safe_text, pii_was_found = check_pii(text)
    assert pii_was_found is True
    assert placeholder in safe_text


def test_clean_text_passes_through_untouched():
    text = "The victim was harassed via repeated messages over several weeks."
    safe_text, pii_was_found = check_pii(text)
    assert pii_was_found is False
    assert safe_text == text


# ---------------------------------------------------------------------------
# Guard construction
# ---------------------------------------------------------------------------


def test_guard_is_built_once():
    assert _get_pii_guard() is _get_pii_guard()
