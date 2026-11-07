"""SCRUM-69: збереження тайтлів у БД (media_titles)."""

from collections.abc import Callable
from datetime import date

import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import Connection, func, select

from app.models import MediaTitle
from tests.qa.conftest import STEAM_API_URL, TMDB_BASE_URL, random_external_id

pytestmark = pytest.mark.database


def test_title_is_saved_once_and_then_served_from_db(
    api_client: TestClient,
    external_api: respx.MockRouter,
    register: Callable[[], dict],
    db: Connection,
) -> None:
    """Перше відкриття тягне дані з TMDB і зберігає; повторне бере з БД без запиту."""
    register()
    series_id = random_external_id()
    route = external_api.get(f"{TMDB_BASE_URL}/tv/{series_id}").respond(
        200,
        json={
            "name": "Темрява",
            "original_name": "Dark",
            "overview": "Зникнення дітей у маленькому містечку.",
            "first_air_date": "2017-12-01",
            "number_of_seasons": 3,
            "genres": [{"name": "Драма"}],
        },
    )

    first = api_client.get(f"/api/titles/tmdb/series/{series_id}")
    second = api_client.get(f"/api/titles/tmdb/series/{series_id}")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()
    assert first.json()["title"]["seasons_count"] == 3
    assert route.call_count == 1, "повторне відкриття не має йти в TMDB"
    rows = db.execute(
        select(func.count())
        .select_from(MediaTitle)
        .where(MediaTitle.provider == "tmdb", MediaTitle.external_id == series_id)
    ).scalar_one()
    assert rows == 1


def test_game_is_saved_with_normalized_fields(
    api_client: TestClient,
    external_api: respx.MockRouter,
    register: Callable[[], dict],
    db: Connection,
) -> None:
    """Гра зі Steam зберігається з провайдером rawg, датою, жанрами й очищеним описом."""
    register()
    app_id = random_external_id()
    external_api.get(f"{STEAM_API_URL}/appdetails").respond(
        200,
        json={
            app_id: {
                "success": True,
                "data": {
                    "name": "The Witcher 3: Wild Hunt",
                    "short_description": "<b>Відьмак</b> &amp; відкритий світ",
                    "release_date": {"date": "18 May, 2015"},
                    "genres": [{"description": "RPG"}, {"description": "Action"}],
                },
            }
        },
    )

    response = api_client.get(f"/api/titles/rawg/game/{app_id}")

    assert response.status_code == 200
    row = db.execute(
        select(
            MediaTitle.id,
            MediaTitle.provider,
            MediaTitle.media_type,
            MediaTitle.title,
            MediaTitle.description,
            MediaTitle.description_language,
            MediaTitle.release_date,
            MediaTitle.genres,
            MediaTitle.poster_url,
        ).where(MediaTitle.external_id == app_id)
    ).one()
    assert str(row.id) == response.json()["title"]["id"]
    assert row.provider == "rawg"
    assert row.media_type == "game"
    assert row.title == "The Witcher 3: Wild Hunt"
    assert row.description == "Відьмак & відкритий світ"
    assert row.description_language == "uk"
    assert row.release_date == date(2015, 5, 18)
    assert row.genres == "RPG, Action"
    assert row.poster_url.endswith(f"/steam/apps/{app_id}/library_600x900.jpg")
