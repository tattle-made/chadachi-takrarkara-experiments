from sqlmodel import Session

from app.models import UserRole
from tests.conftest import auth_headers, make_access_token, make_user


# ---------------------------------------------------------------------------
# GET /users/me
# ---------------------------------------------------------------------------


def test_get_me_authenticated(client, admin_user, admin_token):
    response = client.get("/api/v1/users/me", headers=auth_headers(admin_token))
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == admin_user.email
    assert body["role"] == UserRole.admin.value


def test_get_me_unauthenticated(client):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_get_me_invalid_token(client):
    response = client.get("/api/v1/users/me", headers=auth_headers("bad.token.here"))
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /users/me/password
# ---------------------------------------------------------------------------


def test_change_password_success(client, session: Session, member_user, member_token):
    response = client.patch(
        "/api/v1/users/me/password",
        headers=auth_headers(member_token),
        json={"current_password": "testpassword123", "new_password": "newpassword456"},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Password updated"}

    # Old password should no longer work
    login = client.post(
        "/api/v1/auth/login",
        data={"username": member_user.email, "password": "testpassword123"},
    )
    assert login.status_code == 401


def test_change_password_wrong_current(client, member_token):
    response = client.patch(
        "/api/v1/users/me/password",
        headers=auth_headers(member_token),
        json={"current_password": "wrongpassword", "new_password": "newpassword456"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect current password"


def test_change_password_too_short(client, member_token):
    response = client.patch(
        "/api/v1/users/me/password",
        headers=auth_headers(member_token),
        json={"current_password": "testpassword123", "new_password": "short"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /users/
# ---------------------------------------------------------------------------


def test_create_user_as_admin(client, admin_token):
    response = client.post(
        "/api/v1/users/",
        headers=auth_headers(admin_token),
        json={"email": "new@test.com", "password": "newpassword123", "role": "member"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "new@test.com"
    assert body["role"] == "member"
    assert "id" in body


def test_create_user_as_member_forbidden(client, member_token):
    response = client.post(
        "/api/v1/users/",
        headers=auth_headers(member_token),
        json={"email": "another@test.com", "password": "password123", "role": "member"},
    )
    assert response.status_code == 403


def test_create_user_as_manager_forbidden(client, manager_token):
    response = client.post(
        "/api/v1/users/",
        headers=auth_headers(manager_token),
        json={"email": "another@test.com", "password": "password123", "role": "member"},
    )
    assert response.status_code == 403


def test_create_user_duplicate_email(client, session: Session, admin_token):
    make_user(session, "existing@test.com")

    response = client.post(
        "/api/v1/users/",
        headers=auth_headers(admin_token),
        json={
            "email": "existing@test.com",
            "password": "password123",
            "role": "member",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"


# ---------------------------------------------------------------------------
# GET /users/
# ---------------------------------------------------------------------------


def test_list_users_as_admin(client, admin_user, admin_token, member_user):
    response = client.get("/api/v1/users/", headers=auth_headers(admin_token))
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert "count" in body
    assert body["count"] >= 2


def test_list_users_as_member_forbidden(client, member_token):
    response = client.get("/api/v1/users/", headers=auth_headers(member_token))
    assert response.status_code == 403


def test_list_users_pagination(client, session: Session, admin_token, admin_user):
    make_user(session, "u1@test.com")
    make_user(session, "u2@test.com")

    response = client.get(
        "/api/v1/users/?skip=0&limit=2",
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) <= 2


# ---------------------------------------------------------------------------
# PATCH /users/{id}/archive  &  /users/{id}/unarchive
# ---------------------------------------------------------------------------


def test_archive_user(client, session: Session, admin_token, admin_user):
    target = make_user(session, "target@test.com")

    response = client.patch(
        f"/api/v1/users/{target.id}/archive",
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 200
    assert response.json() == {"message": "User archived"}

    session.refresh(target)
    assert target.is_active is False


def test_archive_user_not_found(client, admin_token):
    response = client.patch(
        "/api/v1/users/999999/archive",
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 404


def test_archive_user_as_member_forbidden(client, session: Session, member_token):
    target = make_user(session, "target@test.com")

    response = client.patch(
        f"/api/v1/users/{target.id}/archive",
        headers=auth_headers(member_token),
    )
    assert response.status_code == 403


def test_unarchive_user(client, session: Session, admin_token, admin_user):
    target = make_user(session, "archived@test.com", is_active=False)

    response = client.patch(
        f"/api/v1/users/{target.id}/unarchive",
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 200
    assert response.json() == {"message": "User unarchived"}

    session.refresh(target)
    assert target.is_active is True


def test_unarchive_user_not_found(client, admin_token):
    response = client.patch(
        "/api/v1/users/999999/unarchive",
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Inactive user cannot authenticate
# ---------------------------------------------------------------------------


def test_inactive_user_blocked_by_token_validation(client, session: Session):
    user = make_user(session, "inactive@test.com", is_active=False)
    token = make_access_token(user)

    response = client.get("/api/v1/users/me", headers=auth_headers(token))
    assert response.status_code == 400
    assert response.json()["detail"] == "Inactive user"
