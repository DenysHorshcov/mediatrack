"""SCRUM-69: сторінка тайтлу (TMDB і Steam замокані через respx)."""

from collections.abc import Callable

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import Connection, func, select

from app.models import MediaTitle
from tests.qa.conftest import STEAM_API_URL, TMDB_BASE_URL, random_external_id

pytestmark = pytest.mark.database


def test_movie_page_falls_back_to_english_description(
    api_client: TestClient,
    external_api: respx.MockRouter,
    register: Callable[[], dict],
) -> None:
    """Якщо українського опису немає, сторінка фільму показує англійський з позначкою en."""
    register()
    movie_id = random_external_id()

    def tmdb_movie(request: httpx.Request) -> httpx.Response:
        language = request.url.params["language"]
        overview = "" if language == "uk-UA" else "A hacker learns the truth."
        return httpx.Response(
            200,
            json={
                "title": "Матриця",
                "original_title": "The Matrix",
                "overview": overview,
                "release_date": "1999-03-30",
                "poster_path": "/matrix.jpg",
                "genres": [{"name": "Фантастика"}, {"name": "Бойовик"}],
            },
        )

    route = external_api.get(f"{TMDB_BASE_URL}/movie/{movie_id}").mock(
        side_effect=tmdb_movie
    )

    response = api_client.get(f"/api/titles/tmdb/movie/{movie_id}")

    assert response.status_code == 200
    title = response.json()["title"]
    assert title["title"] == "Матриця"
    assert title["original_title"] == "The Matrix"
    assert title["description"] == "A hacker learns the truth."
    assert title["description_language"] == "en"
    assert title["year"] == 1999
    assert title["genres"] == ["Фантастика", "Бойовик"]
    assert [c.request.url.params["language"] for c in route.calls] == ["uk-UA", "en-US"]


def test_unknown_game_page_returns_404_and_saves_nothing(
    api_client: TestClient,
    external_api: respx.MockRouter,
    register: Callable[[], dict],
    db: Connection,
) -> None:
    """Гра, якої немає в Steam, дає 404, і в БД нічого не з'являється."""
    register()
    app_id = random_external_id()
    external_api.get(f"{STEAM_API_URL}/appdetails").respond(
        200, json={app_id: {"success": False}}
    )

    response = api_client.get(f"/api/titles/rawg/game/{app_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Такого тайтлу немає"}
    saved = db.execute(
        select(func.count()).select_from(MediaTitle).where(MediaTitle.external_id == app_id)
    ).scalar_one()
    assert saved == 0
