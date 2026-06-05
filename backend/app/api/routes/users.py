from fastapi import APIRouter, HTTPException

from app import crud
from app.api.deps import AdminDep, CurrentUserDep, SessionDep
from app.core.security import get_password_hash, verify_password
from app.models import PasswordChange, UserCreate, UserPublic, UsersPublic

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
def read_current_user(current_user: CurrentUserDep) -> UserPublic:
    return current_user


@router.patch("/me/password")
def change_my_password(
    session: SessionDep,
    current_user: CurrentUserDep,
    body: PasswordChange,
) -> dict[str, str]:
    verified, _ = verify_password(body.current_password, current_user.hashed_password)
    if not verified:
        raise HTTPException(status_code=400, detail="Incorrect current password")
    current_user.hashed_password = get_password_hash(body.new_password)
    session.add(current_user)
    session.commit()
    return {"message": "Password updated"}


@router.post("/", response_model=UserPublic)
def create_user(session: SessionDep, user_in: UserCreate, _: AdminDep) -> UserPublic:
    existing = crud.get_user_by_email(session=session, email=user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(session=session, user_create=user_in)


@router.get("/", response_model=UsersPublic)
def list_users(
    session: SessionDep,
    _: AdminDep,
    skip: int = 0,
    limit: int = 100,
) -> UsersPublic:
    users = crud.get_users(session=session, skip=skip, limit=limit)
    return UsersPublic(data=users, count=len(users))


@router.patch("/{user_id}/archive")
def archive_user(session: SessionDep, _: AdminDep, user_id: int) -> dict[str, str]:
    user = crud.get_user_by_id(session=session, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    session.add(user)
    session.commit()
    return {"message": "User archived"}


@router.patch("/{user_id}/unarchive")
def unarchive_user(session: SessionDep, _: AdminDep, user_id: int) -> dict[str, str]:
    user = crud.get_user_by_id(session=session, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    session.add(user)
    session.commit()
    return {"message": "User unarchived"}
