"""SCRUM-26: статистика профілю (/api/me/stats)."""

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, update

from app.models import LibraryEntry

pytestmark = pytest.mark.database

EMPTY_STATS = {
    "total": 0,
    "by_type": {"movie": 0, "series": 0, "game": 0},
    "by_status": {
        "planned": 0,
        "in_progress": 0,
        "completed": 0,
        "on_hold": 0,
        "dropped": 0,
    },
    "average_rating": None,
    "completed_this_year": 0,
}


def _stats(client: TestClient) -> dict:
    response = client.get("/api/me/stats")
    assert response.status_code == 200
    return response.json()


def _put(client: TestClient, title_id: UUID, status: str) -> None:
    response = client.put(f"/api/me/titles/{title_id}", json={"status": status})
    assert response.status_code == 200


def _rate(client: TestClient, title_id: UUID, rating: int) -> None:
    response = client.patch(f"/api/me/titles/{title_id}", json={"rating": rating})
    assert response.status_code == 200


def test_stats_reflect_user_library(
    api_client: TestClient,
    register: Callable[[], dict],
    make_title: Callable[..., UUID],
) -> None:
    """Статистика рахує тайтли за типами й статусами, середню оцінку і завершені за рік."""
    register()
    movie = make_title(media_type="movie")
    dropped_movie = make_title(media_type="movie")
    series = make_title(media_type="series")
    game = make_title(media_type="game")

    _put(api_client, movie, "completed")
    _rate(api_client, movie, 9)
    _put(api_client, series, "in_progress")
    _rate(api_client, series, 6)
    _put(api_client, game, "planned")
    _put(api_client, dropped_movie, "dropped")

    assert _stats(api_client) == {
        "total": 4,
        "by_type": {"movie": 2, "series": 1, "game": 1},
        "by_status": {
            "planned": 1,
            "in_progress": 1,
            "completed": 1,
            "on_hold": 0,
            "dropped": 1,
        },
        "average_rating": 7.5,
        "completed_this_year": 1,
    }


def test_stats_are_per_user_and_update_after_removal(
    api_client: TestClient,
    register: Callable[[], dict],
    make_title: Callable[..., UUID],
) -> None:
    """Користувач бачить лише свою статистику; після видалення тайтлу вона оновлюється."""
    first_user = register()
    _put(api_client, make_title(media_type="movie"), "completed")
    _put(api_client, make_title(media_type="game"), "planned")

    register()
    assert _stats(api_client) == EMPTY_STATS
    title = make_title(media_type="series")
    _rate(api_client, title, 10)
    assert _stats(api_client)["average_rating"] == 10.0
    assert api_client.delete(f"/api/me/titles/{title}").status_code == 204
    assert _stats(api_client) == EMPTY_STATS

    api_client.cookies.clear()
    login = api_client.post(
        "/api/auth/login", json={"email": first_user["email"], "password": "goodpass1"}
    )
    assert login.status_code == 200
    stats = _stats(api_client)
    assert (stats["total"], stats["by_status"]["completed"]) == (2, 1)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG: completed_this_year рахує за updated_at, тож тайтл, завершений "
        "торік, потрапляє в «цього року» після будь-якої зміни (відгук, оцінка). "
        "Коли баг виправлять, тест почне проходити — тоді прибрати xfail."
    ),
)
def test_completed_last_year_not_counted_after_review_this_year(
    api_client: TestClient,
    register: Callable[[], dict],
    make_title: Callable[..., UUID],
    db: Connection,
) -> None:
    """Тайтл, завершений минулого року, не рахується як «завершено цього року»."""
    register()
    title = make_title(media_type="movie")
    _put(api_client, title, "completed")
    last_year = datetime(datetime.now(UTC).year - 1, 6, 1, tzinfo=UTC)
    db.execute(
        update(LibraryEntry)
        .where(LibraryEntry.title_id == title)
        .values(updated_at=last_year, completed_at=last_year)
    )
    assert _stats(api_client)["completed_this_year"] == 0

    response = api_client.patch(f"/api/me/titles/{title}", json={"review": "Переглянув"})
    assert response.status_code == 200

    assert _stats(api_client)["completed_this_year"] == 0
