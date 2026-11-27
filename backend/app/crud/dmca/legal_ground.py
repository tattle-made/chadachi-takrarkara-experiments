"""DB functions for legal grounds.

Delete is only for grounds no email uses yet; the route checks that first.
Grounds that are in use get turned off with active=False instead.
"""

import uuid
from datetime import datetime, timezone

from sqlmodel import Session, col, select

from app.models.dmca.legal_ground import (
    LegalGround,
    LegalGroundCreate,
    LegalGroundUpdate,
)
from app.models.dmca.takedown_email import TakedownEmailLegalGroundJoin


def create_legal_ground(
    *, session: Session, legal_ground_in: LegalGroundCreate
) -> LegalGround:
    legal_ground = LegalGround.model_validate(legal_ground_in)
    session.add(legal_ground)
    session.commit()
    session.refresh(legal_ground)
    return legal_ground


def list_legal_grounds(
    *, session: Session, include_inactive: bool = False
) -> list[LegalGround]:
    """Active grounds by default; include_inactive=True also returns turned-off ones.

    Ordered by creation, so they show up (and go into emails) in a stable order.
    """
    query = select(LegalGround).order_by(col(LegalGround.created_at))
    if not include_inactive:
        query = query.where(col(LegalGround.active).is_(True))
    return list(session.exec(query))


def get_legal_ground(
    *, session: Session, legal_ground_id: uuid.UUID
) -> LegalGround | None:
    return session.get(LegalGround, legal_ground_id)


def update_legal_ground(
    *,
    session: Session,
    db_legal_ground: LegalGround,
    legal_ground_in: LegalGroundUpdate,
) -> LegalGround:
    # only the fields that were sent, so a PATCH can change just one
    update_data = legal_ground_in.model_dump(exclude_unset=True)
    db_legal_ground.sqlmodel_update(update_data)
    db_legal_ground.updated_at = datetime.now(timezone.utc)
    session.add(db_legal_ground)
    session.commit()
    session.refresh(db_legal_ground)
    return db_legal_ground


def is_legal_ground_used(*, session: Session, legal_ground_id: uuid.UUID) -> bool:
    """Whether any email (draft or sent) uses this ground; then it can't be deleted."""
    # one row in the link table is enough, so stop at the first
    query = select(TakedownEmailLegalGroundJoin).where(
        TakedownEmailLegalGroundJoin.legal_ground_id == legal_ground_id
    )
    return session.exec(query).first() is not None


def delete_legal_ground(*, session: Session, db_legal_ground: LegalGround) -> None:
    # call is_legal_ground_used first. The link table's ondelete="RESTRICT"
    # also makes the DB refuse it, as a backup.
    session.delete(db_legal_ground)
    session.commit()
