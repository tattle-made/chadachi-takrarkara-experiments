"""Reading Google's errors (Gmail and Drive): which are worth a retry, and a
short message to show in UI.

Use GOOGLE_ERRORS to catch only Google's errors, so our own bugs still surface
as a 500 with a full log.
"""

import json

import httplib2  # type: ignore[import-untyped]
from google.auth.exceptions import RefreshError, TransportError
from googleapiclient.errors import HttpError  # type: ignore[import-untyped]

from app.services.google_auth import GoogleNotConnected

# HTTP codes worth retrying: too many requests, and Google-side errors
RETRY_STATUS = {429, 500, 502, 503, 504}
# Gmail also reports rate limits as a 403 with one of these reasons (older
# style in "errors", newer style in "details"; a body can have both)
RATE_LIMIT_REASONS = {
    "rateLimitExceeded",
    "userRateLimitExceeded",
    "RATE_LIMIT_EXCEEDED",
}
# can't reach Google: no network, timeouts, or the token refresh failing on
# the network
NETWORK_ERRORS = (OSError, httplib2.HttpLib2Error, TransportError)
# everything a Gmail or Drive call can raise because of Google
GOOGLE_ERRORS = (HttpError, RefreshError, GoogleNotConnected, *NETWORK_ERRORS)


def is_retryable(err: Exception) -> bool:
    """Rate limits, Google-side errors and network trouble are worth a retry."""
    if isinstance(err, HttpError):
        if err.status_code in RETRY_STATUS:
            return True
        return err.status_code == 403 and bool(reasons(err) & RATE_LIMIT_REASONS)
    return isinstance(err, NETWORK_ERRORS)


def reasons(err: HttpError) -> set[str]:
    """Every "reason" in Google's error body, e.g. {"rateLimitExceeded"}.

    Read from the raw body: HttpError.error_details keeps only one of the two
    lists Google may send ("details" or "errors"). Anything unreadable gives
    an empty set, which counts as "not a rate limit".
    """
    try:
        error = json.loads(err.content)["error"]
        items = [*error.get("errors", []), *error.get("details", [])]
    except (ValueError, KeyError, TypeError, AttributeError):
        return set()
    return {i["reason"] for i in items if isinstance(i, dict) and "reason" in i}


def describe(err: Exception) -> str:
    """A short message for the counsellor, using Google's own words where it
    gives some, e.g. "Google error 404: File not found: 1AbC"."""
    if isinstance(err, GoogleNotConnected):
        return f"{err}. An admin can reconnect it in Config."
    if isinstance(err, HttpError):
        return f"Google error {err.status_code}: {err.reason}"
    if isinstance(err, RefreshError):
        # args[0] is Google's message; the rest is the raw response
        return f"Google refused the app's access: {err.args[0] if err.args else err}"
    if isinstance(err, NETWORK_ERRORS):
        return f"Couldn't reach Google ({str(err) or type(err).__name__}). Try again in a bit."
    return str(err) or type(err).__name__
