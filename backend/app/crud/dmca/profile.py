"""DB functions for profiles."""

import uuid
from datetime import datetime, timezone

from sqlmodel import Session, col, or_, select

from app.models.dmca.profile import Profile, ProfileCreate, ProfileUpdate


def create_profile(
    *, session: Session, profile_in: ProfileCreate, created_by: int
) -> Profile:
    # created_by is the logged-in user, not part of the body
    profile = Profile.model_validate(profile_in, update={"created_by": created_by})
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


def list_profiles(
    *, session: Session, q: str | None = None, skip: int = 0, limit: int = 100
) -> list[Profile]:
    """Newest first. q searches full_name and display_name, ignoring case."""
    query = select(Profile).order_by(col(Profile.created_at).desc())
    if q and q.strip():
        # ilike = case-insensitive LIKE; % matches anything before/after
        pattern = f"%{q.strip()}%"
        query = query.where(
            or_(
                col(Profile.full_name).ilike(pattern),
                col(Profile.display_name).ilike(pattern),
            )
        )
    return list(session.exec(query.offset(skip).limit(limit)))


def get_profile(*, session: Session, profile_id: uuid.UUID) -> Profile | None:
    return session.get(Profile, profile_id)


def update_profile(
    *, session: Session, db_profile: Profile, profile_in: ProfileUpdate
) -> Profile:
    update_data = profile_in.model_dump(exclude_unset=True)
    db_profile.sqlmodel_update(update_data)
    db_profile.updated_at = datetime.now(timezone.utc)
    session.add(db_profile)
    session.commit()
    session.refresh(db_profile)
    return db_profile
