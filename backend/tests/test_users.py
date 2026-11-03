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


REGISTER = {"email": "profile@example.com", "username": "profileuser", "password": "goodpass1"}


def _register(client: TestClient, **overrides: str) -> None:
    body = {**REGISTER, **overrides}
    assert client.post("/api/auth/register", json=body).status_code == 201


def test_get_me_returns_profile(client: TestClient) -> None:
    _register(client)
    response = client.get("/api/users/me")
    assert response.status_code == 200
    user = response.json()["user"]
    assert user["email"] == REGISTER["email"]
    assert user["username"] == REGISTER["username"]
    assert user["avatar_url"] is None


def test_get_me_without_cookie_returns_401(client: TestClient) -> None:
    assert client.get("/api/users/me").status_code == 401


def test_patch_updates_username(client: TestClient) -> None:
    _register(client)
    response = client.patch("/api/users/me", json={"username": "newnick"})
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "newnick"


def test_patch_rejects_empty_username(client: TestClient) -> None:
    _register(client)
    response = client.patch("/api/users/me", json={"username": "   "})
    assert response.status_code == 422
    assert response.json()["fields"]["username"]


def test_patch_rejects_taken_username(client: TestClient) -> None:
    _register(client, email="a@example.com", username="alice")
    client.post("/api/auth/logout")
    _register(client, email="b@example.com", username="bob")
    response = client.patch("/api/users/me", json={"username": "alice"})
    assert response.status_code == 409
    assert response.json()["fields"]["username"]


def test_patch_sets_and_clears_avatar(client: TestClient) -> None:
    _register(client)
    set_response = client.patch(
        "/api/users/me", json={"avatar_url": "https://example.com/a.png"}
    )
    assert set_response.status_code == 200
    assert set_response.json()["user"]["avatar_url"] == "https://example.com/a.png"

    clear_response = client.patch("/api/users/me", json={"avatar_url": ""})
    assert clear_response.status_code == 200
    assert clear_response.json()["user"]["avatar_url"] is None
