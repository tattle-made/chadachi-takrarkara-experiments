from datetime import timedelta

import jwt
import pytest

from app.core.security import (
    ALGORITHM,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.core.config import settings


def test_create_access_token_contains_sub_and_type():
    token = create_access_token(subject="42", expires_delta=timedelta(minutes=5))
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "42"
    assert payload["type"] == "access"
    assert "exp" in payload


def test_create_refresh_token_contains_sub_and_type():
    token = create_refresh_token(subject="7", expires_delta=timedelta(days=1))
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "7"
    assert payload["type"] == "refresh"


def test_access_and_refresh_tokens_differ():
    access = create_access_token(subject="1", expires_delta=timedelta(minutes=5))
    refresh = create_refresh_token(subject="1", expires_delta=timedelta(days=1))
    assert access != refresh


def test_decode_token_roundtrip():
    token = create_access_token(subject="99", expires_delta=timedelta(minutes=10))
    payload = decode_token(token)
    assert payload["sub"] == "99"
    assert payload["type"] == "access"


def test_decode_token_raises_on_expired():
    token = create_access_token(subject="1", expires_delta=timedelta(seconds=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)


def test_decode_token_raises_on_tampered():
    token = create_access_token(subject="1", expires_delta=timedelta(minutes=5))
    tampered = token + "x"
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(tampered)


def test_password_hash_and_verify_roundtrip():
    hashed = get_password_hash("mysecretpassword")
    verified, _ = verify_password("mysecretpassword", hashed)
    assert verified is True


def test_verify_password_wrong_password():
    hashed = get_password_hash("correctpassword")
    verified, _ = verify_password("wrongpassword", hashed)
    assert verified is False


def test_get_password_hash_is_not_plaintext():
    password = "plaintext"
    hashed = get_password_hash(password)
    assert hashed != password


def test_different_passwords_produce_different_hashes():
    h1 = get_password_hash("password1")
    h2 = get_password_hash("password2")
    assert h1 != h2
