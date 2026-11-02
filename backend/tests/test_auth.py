from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.main import app

pytestmark = pytest.mark.database


@pytest.fixture
def client(db: Connection) -> Iterator[TestClient]:
    def override_session() -> Iterator[Session]:
        with Session(bind=db, join_transaction_mode="create_savepoint") as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


REGISTER = {"email": "andrii@example.com", "username": "andrii", "password": "goodpass1"}


def test_register_creates_user_and_sets_cookie(client: TestClient) -> None:
    response = client.post("/api/auth/register", json=REGISTER)
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == REGISTER["email"]
    assert body["user"]["username"] == REGISTER["username"]
    assert "mediatrack_session" in response.cookies


def test_register_duplicate_email_returns_field_error(client: TestClient) -> None:
    client.post("/api/auth/register", json=REGISTER)
    response = client.post(
        "/api/auth/register",
        json={**REGISTER, "username": "another"},
    )
    assert response.status_code == 409
    assert response.json()["fields"]["email"]


def test_register_rejects_short_password(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={**REGISTER, "password": "short"},
    )
    assert response.status_code == 422
    assert response.json()["fields"]["password"]


def test_login_wrong_password_returns_401(client: TestClient) -> None:
    client.post("/api/auth/register", json=REGISTER)
    response = client.post(
        "/api/auth/login",
        json={"email": REGISTER["email"], "password": "wrongpass"},
    )
    assert response.status_code == 401


def test_login_then_me_returns_user(client: TestClient) -> None:
    client.post("/api/auth/register", json=REGISTER)
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["user"]["email"] == REGISTER["email"]


def test_me_without_cookie_returns_401(client: TestClient) -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_logout_clears_session(client: TestClient) -> None:
    client.post("/api/auth/register", json=REGISTER)
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401
