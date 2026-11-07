"""SCRUM-69: пошук ігор (Steam Store API замоканий через respx).

У задачі вказано RAWG, але з SCRUM-58 ігри шукаються через Steam Store API.
"""

import httpx
import respx
from fastapi.testclient import TestClient

from tests.qa.conftest import STEAM_API_URL, TMDB_BASE_URL

STEAM_SEARCH_URL = f"{STEAM_API_URL}/storesearch/"
CAPSULE = "https://cdn.cloudflare.steamstatic.com/steam/apps/{}/library_600x900.jpg"


def test_game_search_returns_steam_games_without_noise(
    search_client: TestClient, external_api: respx.MockRouter
) -> None:
    """Пошук type=game повертає ігри зі Steam і відкидає саундтреки та DLC."""
    steam = external_api.get(STEAM_SEARCH_URL).respond(
        200,
        json={
            "total": 3,
            "items": [
                {"id": 292030, "name": "The Witcher 3: Wild Hunt", "tiny_image": "x.jpg"},
                {"id": 378648, "name": "The Witcher 3 Soundtrack"},
                {"id": 20900, "name": "The Witcher: Enhanced Edition"},
            ],
        },
    )
    tmdb = external_api.get(url__startswith=TMDB_BASE_URL)

    response = search_client.get("/api/search", params={"q": " Witcher ", "type": "game"})

    assert response.status_code == 200
    assert response.json()["results"] == [
        {
            "id": "292030",
            "type": "game",
            "title": "The Witcher 3: Wild Hunt",
            "year": None,
            "poster": CAPSULE.format(292030),
        },
        {
            "id": "20900",
            "type": "game",
            "title": "The Witcher: Enhanced Edition",
            "year": None,
            "poster": CAPSULE.format(20900),
        },
    ]
    assert steam.call_count == 1
    assert steam.calls.last.request.url.params["term"] == "Witcher"
    assert not tmdb.called, "для type=game TMDB не має викликатися"


def test_search_all_still_returns_movies_when_steam_is_down(
    search_client: TestClient, external_api: respx.MockRouter
) -> None:
    """Якщо Steam недоступний, загальний пошук не ламається: фільми з TMDB повертаються."""
    external_api.get(STEAM_SEARCH_URL).mock(side_effect=httpx.ConnectTimeout("timeout"))
    external_api.get(f"{TMDB_BASE_URL}/search/multi").respond(
        200,
        json={
            "results": [
                {
                    "media_type": "movie",
                    "id": 603,
                    "title": "Матриця",
                    "release_date": "1999-03-30",
                }
            ]
        },
    )

    response = search_client.get("/api/search", params={"q": "Матриця"})

    assert response.status_code == 200
    results = response.json()["results"]
    assert [(r["type"], r["title"]) for r in results] == [("movie", "Матриця")]
