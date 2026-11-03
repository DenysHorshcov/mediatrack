"""SCRUM-49: реєстрація і вхід."""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.database

SESSION_COOKIE = "mediatrack_session"


def test_register_success(client: TestClient, new_user: dict[str, str]) -> None:
    """Реєстрація з валідними даними створює користувача і одразу логінить."""
    response = client.post("/api/auth/register", json=new_user)

    assert response.status_code == 201
    user = response.json()["user"]
    assert user["email"] == new_user["email"]
    assert user["username"] == new_user["username"]
    assert user["id"]
    assert "password" not in user
    assert "password_hash" not in user

    set_cookie = response.headers["set-cookie"]
    assert SESSION_COOKIE in set_cookie
    assert "httponly" in set_cookie.lower()

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["id"] == user["id"]


def test_register_duplicate_email_ignores_case(
    client: TestClient, new_user: dict[str, str]
) -> None:
    """Повторна реєстрація з тим самим email (в іншому регістрі) відхиляється."""
    assert client.post("/api/auth/register", json=new_user).status_code == 201
    client.cookies.clear()

    response = client.post(
        "/api/auth/register",
        json={
            **new_user,
            "email": new_user["email"].upper(),
            "username": new_user["username"] + "_2",
        },
    )

    assert response.status_code == 409
    body = response.json()
    assert body["detail"] == "Email вже зареєстрований"
    assert body["fields"]["email"] == "Email вже зареєстрований"
    assert SESSION_COOKIE not in response.cookies


def test_login_success(client: TestClient, new_user: dict[str, str]) -> None:
    """Вхід з правильними email і паролем ставить cookie сесії."""
    registered = client.post("/api/auth/register", json=new_user)
    assert registered.status_code == 201
    client.cookies.clear()
    assert client.get("/api/auth/me").status_code == 401

    response = client.post(
        "/api/auth/login",
        json={"email": new_user["email"], "password": new_user["password"]},
    )

    assert response.status_code == 200
    assert response.json()["user"]["id"] == registered.json()["user"]["id"]
    assert SESSION_COOKIE in response.cookies
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["email"] == new_user["email"]


def test_login_invalid_credentials(
    client: TestClient, new_user: dict[str, str]
) -> None:
    """Неправильний пароль і неіснуючий email дають однакову відповідь 401."""
    assert client.post("/api/auth/register", json=new_user).status_code == 201
    client.cookies.clear()

    wrong_password = client.post(
        "/api/auth/login",
        json={"email": new_user["email"], "password": "wrongpass1"},
    )
    unknown_email = client.post(
        "/api/auth/login",
        json={"email": "nobody_" + new_user["email"], "password": new_user["password"]},
    )

    for response in (wrong_password, unknown_email):
        assert response.status_code == 401
        assert response.json() == {"detail": "Неправильний email або пароль"}
        assert SESSION_COOKIE not in response.cookies
    assert client.get("/api/auth/me").status_code == 401
