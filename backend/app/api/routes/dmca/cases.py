"""Cases API: list and edit cases, and add the links being reported.

Cases are created under a profile (POST /dmca/profiles/{id}/cases). Any
logged-in user can do everything here; every counsellor sees every case.
"""

import uuid

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUserDep, SessionDep
from app.crud.dmca.case import (
    add_links,
    delete_link,
    get_active_user,
    get_case,
    get_link,
    list_assignees,
    list_cases,
    update_case,
)
from app.models.dmca.case import (
    Case,
    CaseLinkPublic,
    CaseLinksAdd,
    CaseLinksAdded,
    CasePublic,
    CasesPublic,
    CaseSummary,
    CaseUpdate,
    UserSummary,
)

router = APIRouter(prefix="/dmca", tags=["dmca"])


def get_case_or_404(session: SessionDep, case_id: uuid.UUID) -> Case:
    """Load the case from the URL, or stop with a 404."""
    case = get_case(session=session, case_id=case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.get("/cases", response_model=CasesPublic)
def get_cases(
    session: SessionDep,
    current_user: CurrentUserDep,
    assigned_to_me: bool = False,
    profile_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> CasesPublic:
    """List cases, newest first.

    ?assigned_to_me=true for the "Assigned to me" filter, ?profile_id= for one
    person's cases.
    """
    cases = list_cases(
        session=session,
        assigned_to=current_user.id if assigned_to_me else None,
        profile_id=profile_id,
        skip=skip,
        limit=limit,
    )
    return CasesPublic(
        data=[CaseSummary.model_validate(c) for c in cases], count=len(cases)
    )


@router.get("/cases/{case_id}", response_model=CasePublic)
def get_one_case(
    session: SessionDep, _: CurrentUserDep, case_id: uuid.UUID
) -> CasePublic:
    """Get one case with its profile, assignee and links."""
    case = get_case_or_404(session, case_id)
    return CasePublic.model_validate(case)


@router.patch("/cases/{case_id}", response_model=CasePublic)
def update_one_case(
    session: SessionDep, _: CurrentUserDep, case_id: uuid.UUID, case_in: CaseUpdate
) -> CasePublic:
    """Edit title, is_minor or assignee. {"assigned_to": null} unassigns."""
    case = get_case_or_404(session, case_id)
    if case_in.assigned_to is not None and not get_active_user(
        session=session, user_id=case_in.assigned_to
    ):
        raise HTTPException(status_code=400, detail="Assignee not found")
    updated = update_case(session=session, db_case=case, case_in=case_in)
    return CasePublic.model_validate(updated)


@router.get("/assignees", response_model=list[UserSummary])
def get_assignees(session: SessionDep, _: CurrentUserDep) -> list[UserSummary]:
    """Users a case can be assigned to, for the assignee picker.

    Needed because GET /users is admin-only.
    """
    return [UserSummary.model_validate(u) for u in list_assignees(session=session)]


# --- links ---


@router.post("/cases/{case_id}/links", response_model=CaseLinksAdded)
def add_case_links(
    session: SessionDep, _: CurrentUserDep, case_id: uuid.UUID, body: CaseLinksAdd
) -> CaseLinksAdded:
    """Add the links a counsellor pasted (spaces, new lines or commas between them).

    Body: {"text": "https://example-site.com/a\\nexample-site.com/b"}
    Returns which were added, which the case already had, and which weren't
    links, so the UI can tell the counsellor.
    """
    get_case_or_404(session, case_id)
    added, skipped, invalid = add_links(
        session=session, case_id=case_id, text=body.text
    )
    return CaseLinksAdded(
        added=[CaseLinkPublic.model_validate(link) for link in added],
        skipped=skipped,
        invalid=invalid,
    )


@router.delete("/cases/{case_id}/links/{link_id}")
def delete_case_link(
    session: SessionDep, _: CurrentUserDep, case_id: uuid.UUID, link_id: uuid.UUID
) -> dict[str, str]:
    """Remove a link added by mistake."""
    link = get_link(session=session, link_id=link_id)
    # also check it belongs to this case, so a wrong URL can't delete another
    # case's link
    if link is None or link.case_id != case_id:
        raise HTTPException(status_code=404, detail="Link not found")
    delete_link(session=session, db_link=link)
    return {"message": "Link deleted"}
