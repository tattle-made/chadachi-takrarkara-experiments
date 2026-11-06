"""The takedown email template, and picking which address to send to.

Builds the subject and body of a takedown email. Minor (CSAM) cases use the same
body with "CSAM/DMCA" in the subject and one extra paragraph.

Plain functions with no DB access.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.models.dmca.enums import EmailType

# the extra paragraph for minor cases (legal wording: keep it as is)
MINOR_PARAGRAPH = (
    "It also goes against the guidelines of the Indian POCSO Act, 2012 and the "
    "Information Technology (IT) Act, 2000, and Bhartiya Nyay Samhita 2023 for "
    "publishing, transmitting or viewing child sexual abuse and exploitation "
    "material online and is a punishable offence. The child's age proof has been "
    "verified as well and attached herewith."
)

# which address type to try first when the counsellor didn't pick one
ADULT_ORDER = [EmailType.dmca, EmailType.abuse, EmailType.general]
MINOR_ORDER = [EmailType.csam, EmailType.dmca, EmailType.abuse, EmailType.general]


# --- small inputs, so the template doesn't depend on the DB tables ---


@dataclass
class LinkInput:
    url: str
    domain: str


@dataclass
class GroundInput:
    citation: str
    clause_text: str


@dataclass
class AddressInput:
    address: str
    email_type: EmailType


# --- subject and body ---


def unique_domains(links: Sequence[LinkInput]) -> list[str]:
    """Each domain once, in the order the links come in."""
    return list(dict.fromkeys(link.domain for link in links))


def build_subject(domains: Sequence[str], is_minor: bool) -> str:
    """e.g. "DMCA Takedown Request – a.com, b.com, c.com +2 more"."""
    shown = ", ".join(domains[:3])
    extra = f" +{len(domains) - 3} more" if len(domains) > 3 else ""
    prefix = "CSAM/DMCA" if is_minor else "DMCA"
    return f"{prefix} Takedown Request – {shown}{extra}"


def render_body(
    *,
    full_name: str,
    recipient_name: str,
    links: Sequence[LinkInput],
    legal_grounds: Sequence[GroundInput],
    is_minor: bool,
) -> str:
    """Fill in the email body. Paragraphs are separated by a blank line."""
    domains = unique_domains(links)

    # one domain: just the URLs. Several: URLs grouped under their domain
    if len(domains) <= 1:
        links_block = "\n".join(link.url for link in links)
    else:
        groups = []
        for domain in domains:
            urls = [f"  {link.url}" for link in links if link.domain == domain]
            groups.append(f"{domain}:\n" + "\n".join(urls))
        links_block = "\n".join(groups)

    breach = (
        f"This incident unequivocally breaches {recipient_name}'s copyright "
        "infringement policy"
    )
    if legal_grounds:
        grounds = "\n".join(f"- {g.citation}: {g.clause_text}" for g in legal_grounds)
        grounds_block = f"{breach}, along with the following:\n{grounds}"
    else:
        grounds_block = f"{breach}."

    paragraphs: list[str | None] = [
        "Hi,",
        "This letter serves as official notification of copyright infringement "
        'pursuant to the Digital Millennium Copyright Act ("DMCA") 17 U.S.C. '
        f"§ 512(c)(3) for materials on {', '.join(domains)}",
        f"{full_name} is the exclusive rights holder of the following copyrighted "
        "material that is posted without authorization on your website at the "
        f"following link:\n{links_block}",
        f"The uploaded content is the possession of {full_name} and the video has "
        "been uploaded without her consent.",
        f"Upon receipt of this notice, {full_name} requests that you expeditiously "
        "remove or disable access to the materials identified above as being the "
        "subject of infringement.",
        f"{full_name} is providing this notice in good faith and with the "
        "reasonable belief that their rights as the exclusive rights holder are "
        "being infringed.",
        f"Under penalty of perjury, {full_name} certifies that the information "
        "contained in this notification is both true and accurate and that they "
        "are the owner of the copyrighted material identified above.",
        grounds_block,
        "Furthermore, the unauthorized dissemination of non-consensual intimate "
        "material flagrantly violates Indian laws, including the Bharatiya Nayaya "
        "Sanhita 2023 and the Information Technology (IT) Act, 2000. These laws "
        "categorically prohibit and criminalize the publishing and transmission "
        "of such material, making this a punishable offense. A cybercrime report "
        "has been filed.",
        MINOR_PARAGRAPH if is_minor else None,
        # TODO: the "Attachments:" block goes here once attachments are built
        "We implore you to take swift and decisive action to remove this content "
        "from your platform immediately. Failure to act promptly not only "
        "exacerbates the victim's trauma but also undermines your commitment to "
        "uphold the principles of the DMCA and relevant intellectual property laws.",
        "If you wish to discuss the matter further, please reply to this email.",
        "We appreciate your prompt attention to this matter.",
    ]
    return "\n\n".join(p for p in paragraphs if p is not None)


# --- address ---


def pick_address(
    addresses: Sequence[AddressInput], *, is_minor: bool, wanted: EmailType | None
) -> tuple[EmailType, str] | None:
    """Which of a recipient's addresses to send to: (type, address), or None.

    - wanted given (the dropdown): an address of that type. ValueError if the
      recipient has none, since the dropdown only offers types it has.
    - wanted left out: the first type in the default order that it has.
    If the recipient has several addresses of one type, the first one wins, so
    pass them oldest first.
    """
    first_of_type: dict[EmailType, str] = {}
    for a in addresses:
        # setdefault only sets it the first time, so the oldest address stays
        first_of_type.setdefault(a.email_type, a.address)

    if wanted is not None:
        if wanted not in first_of_type:
            raise ValueError(f"no {wanted.value} address")
        return wanted, first_of_type[wanted]

    for email_type in MINOR_ORDER if is_minor else ADULT_ORDER:
        if email_type in first_of_type:
            return email_type, first_of_type[email_type]
    return None
