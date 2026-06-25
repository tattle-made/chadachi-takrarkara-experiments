from pathlib import Path

# Must be set before any app imports so Settings() initialises correctly.
# Load from .env.test at the repo root (two levels above this tests/ directory).
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env.test", override=True)

from collections.abc import Generator
from datetime import timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

from app.api.deps import get_session
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
)
from app.main import app
from app.models import (
    Conversation,
    FunctionalityType,
    Message,
    MessageKind,
    MessageStatus,
    User,
    UserRole,
)


@pytest.fixture(scope="function")
def engine():
    _engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(_engine)
    yield _engine
    SQLModel.metadata.drop_all(_engine)


@pytest.fixture(scope="function")
def session(engine) -> Generator[Session, None, None]:
    with Session(engine) as sess:
        yield sess


@pytest.fixture(scope="function")
def client(session) -> Generator[TestClient, None, None]:
    def _override():
        yield session

    app.dependency_overrides[get_session] = _override

    # Patch init_db so the startup event doesn't attempt a PostgreSQL connection
    with patch("app.main.init_db"):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_user(
    session: Session,
    email: str,
    password: str = "testpassword123",
    role: UserRole = UserRole.member,
    is_active: bool = True,
) -> User:
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        role=role,
        is_active=is_active,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def make_access_token(user: User) -> str:
    return create_access_token(subject=user.id, expires_delta=timedelta(minutes=30))


def make_refresh_token(user: User) -> str:
    return create_refresh_token(subject=user.id, expires_delta=timedelta(days=7))


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def make_conversation(session: Session, user: User) -> Conversation:
    conv = Conversation(
        user_id=user.id,
        functionality_type=FunctionalityType.write_email,
    )
    session.add(conv)
    session.commit()
    session.refresh(conv)
    return conv


def make_message(
    session: Session,
    conversation: Conversation,
    user: User,
    body: str = "Email body text",
) -> Message:
    msg = Message(
        conversation_id=conversation.id,
        user_id=user.id,
        kind=MessageKind.llm_response,
        functionality_type=FunctionalityType.write_email,
        body=body,
        status=MessageStatus.completed,
    )
    session.add(msg)
    session.commit()
    session.refresh(msg)
    return msg


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_user(session: Session) -> User:
    return make_user(session, "admin@test.com", role=UserRole.admin)


@pytest.fixture
def member_user(session: Session) -> User:
    return make_user(session, "member@test.com", role=UserRole.member)


@pytest.fixture
def manager_user(session: Session) -> User:
    return make_user(session, "manager@test.com", role=UserRole.manager)


@pytest.fixture
def admin_token(admin_user: User) -> str:
    return make_access_token(admin_user)


@pytest.fixture
def member_token(member_user: User) -> str:
    return make_access_token(member_user)


@pytest.fixture
def manager_token(manager_user: User) -> str:
    return make_access_token(manager_user)
