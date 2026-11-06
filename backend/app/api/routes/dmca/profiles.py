"""Profiles API: the people takedowns are for.

Any logged-in user can do everything here, since counsellors create and edit
profiles. Profiles can't be deleted.
"""

import uuid

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUserDep, SessionDep
from app.crud.dmca.case import create_case, get_active_user
from app.crud.dmca.profile import (
    create_profile,
    get_profile,
    list_profiles,
    update_profile,
)
from app.models.dmca.case import CaseCreate, CasePublic, ProfileDetail
from app.models.dmca.profile import (
    Profile,
    ProfileCreate,
    ProfilesPublic,
    ProfileSummary,
    ProfileUpdate,
)

router = APIRouter(prefix="/dmca/profiles", tags=["dmca"])


def get_profile_or_404(session: SessionDep, profile_id: uuid.UUID) -> Profile:
    """Load the profile from the URL, or stop with a 404."""
    profile = get_profile(session=session, profile_id=profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.get("", response_model=ProfilesPublic)
def get_profiles(
    session: SessionDep,
    _: CurrentUserDep,
    q: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> ProfilesPublic:
    """List profiles, newest first. ?q= searches full and display names."""
    profiles = list_profiles(session=session, q=q, skip=skip, limit=limit)
    return ProfilesPublic(
        data=[ProfileSummary.model_validate(p) for p in profiles],
        count=len(profiles),
    )


@router.post("", response_model=ProfileDetail)
def create_new_profile(
    session: SessionDep, current_user: CurrentUserDep, profile_in: ProfileCreate
) -> ProfileDetail:
    """Create a profile. full_name is required, display_name is optional."""
    # current_user.id is never None for a logged-in user; the assert tells
    # the type checker that
    assert current_user.id is not None
    profile = create_profile(
        session=session, profile_in=profile_in, created_by=current_user.id
    )
    return ProfileDetail.model_validate(profile)


@router.get("/{profile_id}", response_model=ProfileDetail)
def get_one_profile(
    session: SessionDep, _: CurrentUserDep, profile_id: uuid.UUID
) -> ProfileDetail:
    """Get one profile with its cases."""
    profile = get_profile_or_404(session, profile_id)
    return ProfileDetail.model_validate(profile)


@router.patch("/{profile_id}", response_model=ProfileDetail)
def update_one_profile(
    session: SessionDep,
    _: CurrentUserDep,
    profile_id: uuid.UUID,
    profile_in: ProfileUpdate,
) -> ProfileDetail:
    """Edit names or notes. Fields left out of the body stay as they are."""
    profile = get_profile_or_404(session, profile_id)
    updated = update_profile(session=session, db_profile=profile, profile_in=profile_in)
    return ProfileDetail.model_validate(updated)


@router.post("/{profile_id}/cases", response_model=CasePublic)
def create_profile_case(
    session: SessionDep,
    current_user: CurrentUserDep,
    profile_id: uuid.UUID,
    case_in: CaseCreate,
) -> CasePublic:
    """Open a new case for this profile, optionally assigned to someone."""
    get_profile_or_404(session, profile_id)
    if case_in.assigned_to is not None and not get_active_user(
        session=session, user_id=case_in.assigned_to
    ):
        raise HTTPException(status_code=400, detail="Assignee not found")
    assert current_user.id is not None
    case = create_case(
        session=session,
        profile_id=profile_id,
        case_in=case_in,
        created_by=current_user.id,
    )
    return CasePublic.model_validate(case)
