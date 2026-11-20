"""DB functions for cases and their links."""

import uuid
from datetime import datetime, timezone

from sqlmodel import Session, col, select

from app.models.dmca.case import Case, CaseCreate, CaseLink, CaseUpdate
from app.models.user import User
from app.utils.links import parse_links

# --- cases ---


def create_case(
    *, session: Session, profile_id: uuid.UUID, case_in: CaseCreate, created_by: int
) -> Case:
    # profile_id comes from the URL and created_by from the logged-in user
    case = Case.model_validate(
        case_in, update={"profile_id": profile_id, "created_by": created_by}
    )
    session.add(case)
    session.commit()
    session.refresh(case)
    return case


def list_cases(
    *,
    session: Session,
    assigned_to: int | None = None,
    profile_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Case]:
    """Newest first, optionally only one user's cases or one profile's cases."""
    query = select(Case).order_by(col(Case.created_at).desc())
    if assigned_to is not None:
        query = query.where(Case.assigned_to == assigned_to)
    if profile_id is not None:
        query = query.where(Case.profile_id == profile_id)
    return list(session.exec(query.offset(skip).limit(limit)))


def get_case(*, session: Session, case_id: uuid.UUID) -> Case | None:
    return session.get(Case, case_id)


def update_case(*, session: Session, db_case: Case, case_in: CaseUpdate) -> Case:
    # exclude_unset keeps an explicit "assigned_to": null (= unassign) but drops
    # fields that weren't sent at all
    update_data = case_in.model_dump(exclude_unset=True)
    db_case.sqlmodel_update(update_data)
    db_case.updated_at = datetime.now(timezone.utc)
    session.add(db_case)
    session.commit()
    session.refresh(db_case)
    return db_case


# --- assignees ---


def get_active_user(*, session: Session, user_id: int) -> User | None:
    """The user, if they exist and aren't archived (only they can get cases)."""
    user = session.get(User, user_id)
    return user if user is not None and user.is_active else None


def list_assignees(*, session: Session) -> list[User]:
    """Users a case can be assigned to: everyone who isn't archived."""
    query = select(User).where(col(User.is_active).is_(True)).order_by(col(User.email))
    return list(session.exec(query))


# --- links ---


def add_links(
    *, session: Session, case_id: uuid.UUID, text: str
) -> tuple[list[CaseLink], list[str], list[str]]:
    """Save the links pasted into a case.

    Returns (added, skipped, invalid):
    - added: new CaseLink rows
    - skipped: URLs this case already has (or that were pasted twice)
    - invalid: pieces we couldn't read a domain from; not saved
    """
    parsed = parse_links(text)
    existing = set(
        session.exec(select(CaseLink.url).where(CaseLink.case_id == case_id)).all()
    )

    added: list[CaseLink] = []
    skipped: list[str] = []
    invalid: list[str] = []
    for link in parsed:
        if link.domain is None:
            invalid.append(link.url)
        elif link.url in existing:
            skipped.append(link.url)
        else:
            row = CaseLink(case_id=case_id, url=link.url, domain=link.domain)
            session.add(row)
            added.append(row)

    # one commit for all of them. parse_links already removed duplicates and we
    # skipped the existing ones, so the unique constraint won't trip here
    session.commit()
    for row in added:
        session.refresh(row)
    return added, skipped, invalid


def get_link(*, session: Session, link_id: uuid.UUID) -> CaseLink | None:
    return session.get(CaseLink, link_id)


def delete_link(*, session: Session, db_link: CaseLink) -> None:
    session.delete(db_link)
    session.commit()
