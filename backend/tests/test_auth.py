from sqlmodel import Session

from tests.conftest import auth_headers, make_refresh_token, make_user


def test_login_success(client, session: Session):
    make_user(session, "user@test.com", password="mypassword123")

    response = client.post(
        "/api/v1/auth/login",
        data={"username": "user@test.com", "password": "mypassword123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert "refresh_token" in response.cookies


def test_login_wrong_password(client, session: Session):
    make_user(session, "user@test.com", password="correctpass123")

    response = client.post(
        "/api/v1/auth/login",
        data={"username": "user@test.com", "password": "wrongpass123"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_login_unknown_email(client):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@test.com", "password": "password123"},
    )
    assert response.status_code == 401


def test_login_inactive_user(client, session: Session):
    make_user(session, "inactive@test.com", password="password123", is_active=False)

    response = client.post(
        "/api/v1/auth/login",
        data={"username": "inactive@test.com", "password": "password123"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Inactive user"


def test_refresh_success(client, session: Session):
    user = make_user(session, "user@test.com")
    refresh_tok = make_refresh_token(user)

    response = client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": refresh_tok},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_refresh_no_cookie(client):
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


def test_refresh_with_access_token_rejected(client, session: Session):
    user = make_user(session, "user@test.com")
    from tests.conftest import make_access_token

    access_tok = make_access_token(user)

    response = client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": access_tok},
    )
    assert response.status_code == 401
    assert "refresh token" in response.json()["detail"].lower()


def test_refresh_invalid_token(client):
    response = client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": "not.a.valid.token"},
    )
    assert response.status_code == 401


def test_refresh_inactive_user(client, session: Session):
    user = make_user(session, "user@test.com", is_active=False)
    refresh_tok = make_refresh_token(user)

    response = client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": refresh_tok},
    )
    assert response.status_code == 401


def test_logout_clears_cookie(client, session: Session):
    user = make_user(session, "user@test.com")
    from tests.conftest import make_access_token

    token = make_access_token(user)

    response = client.post(
        "/api/v1/auth/logout",
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Logged out successfully"}
