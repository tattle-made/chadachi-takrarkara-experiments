"""Tests for app/utils/links.py (no DB, plain functions)."""

import pytest

from app.utils.links import extract_domain, parse_links


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://example-site.com/a", "example-site.com"),
        ("http://example-site.com", "example-site.com"),
        ("HTTPS://WWW.Example-Site.com/a?b=c", "example-site.com"),
        # no scheme
        ("example-site.com/a", "example-site.com"),
        ("www.example-site.com", "example-site.com"),
        # subdomains other than www are kept
        ("https://cdn.example-site.com/x.jpg", "cdn.example-site.com"),
        # port and user:password are dropped
        ("http://user:pw@example-site.com:8080/x", "example-site.com"),
        ("  https://example-site.com  ", "example-site.com"),
        # not links
        ("", None),
        ("   ", None),
        ("not-a-link", None),
        ("localhost:3000", None),
        ("https://[broken", None),
    ],
)
def test_extract_domain(raw, expected):
    assert extract_domain(raw) == expected


def test_parse_links_splits_on_spaces_newlines_and_commas():
    text = "https://a.test/1 https://a.test/2\nb.test/3,c.test/4"
    assert [link.url for link in parse_links(text)] == [
        "https://a.test/1",
        "https://a.test/2",
        "b.test/3",
        "c.test/4",
    ]


def test_parse_links_removes_duplicates_keeping_order():
    links = parse_links("b.test/1 a.test/1 b.test/1")
    assert [link.url for link in links] == ["b.test/1", "a.test/1"]


def test_parse_links_keeps_invalid_with_no_domain():
    links = parse_links("a.test/1 hello")
    assert [(link.url, link.domain) for link in links] == [
        ("a.test/1", "a.test"),
        ("hello", None),
    ]


def test_parse_links_empty_text():
    assert parse_links("  \n , ") == []
