"""SCRUM-69: статуси тайтлів у списках користувача."""

from collections.abc import Callable
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.database


def _ids(response) -> list[str]:
    assert response.status_code == 200
    return [item["id"] for item in response.json()["items"]]


def test_status_add_change_and_filter(
    api_client: TestClient,
    register: Callable[[], dict],
    make_title: Callable[..., UUID],
) -> None:
    """Тайтл додається зі статусом, статус змінюється, фільтр списку це враховує."""
    register()
    title_id = str(make_title(media_type="movie", title="Матриця"))

    added = api_client.put(f"/api/me/titles/{title_id}", json={"status": "planned"})
    assert added.status_code == 200
    assert added.json()["entry"]["status"] == "planned"
    assert title_id in _ids(api_client.get("/api/me/titles", params={"status": "planned"}))

    changed = api_client.put(f"/api/me/titles/{title_id}", json={"status": "completed"})
    assert changed.status_code == 200
    assert changed.json()["entry"]["status"] == "completed"

    assert api_client.get(f"/api/me/titles/{title_id}").json()["entry"]["status"] == "completed"
    assert title_id in _ids(api_client.get("/api/me/titles", params={"status": "completed"}))
    assert title_id not in _ids(api_client.get("/api/me/titles", params={"status": "planned"}))
    assert _ids(api_client.get("/api/me/titles")).count(title_id) == 1


def test_user_does_not_see_other_users_list(
    api_client: TestClient,
    register: Callable[[], dict],
    make_title: Callable[..., UUID],
) -> None:
    """Статуси одного користувача не видно іншому."""
    title_id = str(make_title(media_type="game", title="Відьмак 3"))

    register()
    assert (
        api_client.put(f"/api/me/titles/{title_id}", json={"status": "in_progress"})
        .status_code
        == 200
    )

    register()
    assert title_id not in _ids(api_client.get("/api/me/titles"))
    other = api_client.get(f"/api/me/titles/{title_id}")
    assert other.status_code == 404
    assert other.json() == {"detail": "Тайтлу немає у ваших списках"}
