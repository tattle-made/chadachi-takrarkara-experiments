"""Config API: legal grounds (the law clauses a counsellor can tick on an email).

Reads are open to any logged-in user (the draft screen needs them); writes are
admin-only. DELETE works only while no email uses the ground; after that,
PATCH {"active": false} turns it off instead.
"""

import uuid

from fastapi import APIRouter, HTTPException

from app.api.deps import AdminDep, CurrentUserDep, SessionDep
from app.crud.dmca.legal_ground import (
    create_legal_ground,
    delete_legal_ground,
    get_legal_ground,
    is_legal_ground_used,
    list_legal_grounds,
    update_legal_ground,
)
from app.models.dmca.legal_ground import (
    LegalGroundCreate,
    LegalGroundPublic,
    LegalGroundsPublic,
    LegalGroundUpdate,
)

router = APIRouter(prefix="/dmca/legal-grounds", tags=["dmca"])


@router.get("", response_model=LegalGroundsPublic)
def get_legal_grounds(
    session: SessionDep, _: CurrentUserDep, include_inactive: bool = False
) -> LegalGroundsPublic:
    """List legal grounds. Only active ones unless ?include_inactive=true.

    Config passes include_inactive=true to show the turned-off ones as well; the
    draft screen uses the default. Inactive grounds aren't secret, so any user
    may ask for them.
    """
    grounds = list_legal_grounds(session=session, include_inactive=include_inactive)
    return LegalGroundsPublic(
        data=[LegalGroundPublic.model_validate(g) for g in grounds],
        count=len(grounds),
    )


@router.post("", response_model=LegalGroundPublic)
def create_new_legal_ground(
    session: SessionDep, _: AdminDep, legal_ground_in: LegalGroundCreate
) -> LegalGroundPublic:
    """Admin: add a legal ground."""
    legal_ground = create_legal_ground(session=session, legal_ground_in=legal_ground_in)
    return LegalGroundPublic.model_validate(legal_ground)


@router.patch("/{legal_ground_id}", response_model=LegalGroundPublic)
def update_one_legal_ground(
    session: SessionDep,
    _: AdminDep,
    legal_ground_id: uuid.UUID,
    legal_ground_in: LegalGroundUpdate,
) -> LegalGroundPublic:
    """Admin: edit a ground, or turn it off/on with {"active": false | true}.

    Fields left out of the body stay as they are.
    """
    legal_ground = get_legal_ground(session=session, legal_ground_id=legal_ground_id)
    if legal_ground is None:
        raise HTTPException(status_code=404, detail="Legal ground not found")
    updated = update_legal_ground(
        session=session, db_legal_ground=legal_ground, legal_ground_in=legal_ground_in
    )
    return LegalGroundPublic.model_validate(updated)


@router.delete("/{legal_ground_id}")
def delete_one_legal_ground(
    session: SessionDep, _: AdminDep, legal_ground_id: uuid.UUID
) -> dict[str, str]:
    """Admin: delete a ground, e.g. one added by mistake.

    409 if any email already uses it; turn it off with PATCH {"active": false}
    instead.
    """
    legal_ground = get_legal_ground(session=session, legal_ground_id=legal_ground_id)
    if legal_ground is None:
        raise HTTPException(status_code=404, detail="Legal ground not found")
    # checked here (not only by the DB) for a clear message, and because the
    # SQLite tests don't enforce foreign keys
    if is_legal_ground_used(session=session, legal_ground_id=legal_ground_id):
        raise HTTPException(
            status_code=409,
            detail="Existing emails use this legal ground, so it can't be deleted. "
            "Turn it off instead.",
        )
    delete_legal_ground(session=session, db_legal_ground=legal_ground)
    return {"message": "Legal ground deleted"}
