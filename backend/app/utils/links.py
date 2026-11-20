"""Reading pasted links: split the text into URLs and pull out each one's domain."""

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

# links can be separated by spaces, new lines or commas
_SEPARATORS = re.compile(r"[\s,]+")
_HAS_SCHEME = re.compile(r"^https?://", re.IGNORECASE)


@dataclass
class ParsedLink:
    url: str
    # None when no domain could be read, e.g. "not-a-link"
    domain: str | None


def extract_domain(raw: str) -> str | None:
    """The site a link points to, e.g. "https://www.Example-Site.com/a" -> "example-site.com".

    Returns None if it doesn't look like a link.
    """
    text = raw.strip()
    if not text:
        return None
    # "example-site.com/a" has no scheme, and urlsplit then can't find the host
    if not _HAS_SCHEME.match(text):
        text = f"https://{text}"
    try:
        # .hostname is already lowercase, without the port or user:password@
        host = urlsplit(text).hostname
    except ValueError:
        # e.g. a broken IPv6 address like "https://[abc"
        return None
    if not host:
        return None
    # www.example-site.com and example-site.com are the same site for us
    host = host.removeprefix("www.")
    # a real domain has a dot ("localhost" or "hello" isn't one)
    return host if "." in host else None


def parse_links(text: str) -> list[ParsedLink]:
    """Split pasted text into unique links, in the order they were pasted."""
    pieces = [p for p in _SEPARATORS.split(text) if p]
    # dict.fromkeys keeps the first copy of each, in order
    unique = list(dict.fromkeys(pieces))
    return [ParsedLink(url=url, domain=extract_domain(url)) for url in unique]
