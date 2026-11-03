"""SCRUM-49: профіль."""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.database


def test_profile_update_username_is_saved(
    client: TestClient, new_user: dict[str, str]
) -> None:
    """Зміна нікнейму зберігається і повертається при наступному читанні профілю."""
    assert client.post("/api/auth/register", json=new_user).status_code == 201
    new_username = new_user["username"] + "_new"

    response = client.patch("/api/users/me", json={"username": f"  {new_username}  "})

    assert response.status_code == 200
    assert response.json()["user"]["username"] == new_username

    profile = client.get("/api/users/me")
    assert profile.status_code == 200
    user = profile.json()["user"]
    assert user["username"] == new_username
    assert user["email"] == new_user["email"]
