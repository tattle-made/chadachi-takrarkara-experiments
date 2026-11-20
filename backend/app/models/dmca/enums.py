from enum import Enum


class EmailType(str, Enum):
    dmca = "dmca"
    abuse = "abuse"
    csam = "csam"
    general = "general"


class DomainRelation(str, Enum):
    website_owner = "website_owner"
    cdn = "cdn"
    host = "host"
    registrar = "registrar"


class EmailStatus(str, Enum):
    """Where a takedown email is: draft -> queued -> sending -> sent | failed."""

    draft = "draft"  # being edited; the only status that can be changed
    queued = "queued"  # waiting for the background sender to pick it up
    sending = "sending"  # being sent right now
    sent = "sent"  # Gmail accepted it
    failed = "failed"  # gave up after retries; can be retried by hand


class GoogleConnectionStatus(str, Enum):
    connected = "connected"  # working; emails can be sent
    broken = "broken"  # Google refused the token (revoked or expired): reconnect


class AttachmentKind(str, Enum):
    """What a profile's document is. Shown as its label in the email body."""

    cyber_crime_report = "cyber_crime_report"
    government_id = "government_id"
    age_proof = "age_proof"  # for minor cases
    other = "other"  # listed by its file name
