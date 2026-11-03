"""SCRUM-49: пошук фільмів у TMDB (зовнішній API замокано через respx)."""

import httpx
import respx
from fastapi.testclient import TestClient

from tests.qa.conftest import TMDB_TEST_KEY

IMAGE_BASE = "https://image.tmdb.org/t/p/w342"
UNAVAILABLE = "Пошук тимчасово недоступний. Спробуйте пізніше."


def test_search_returns_mapped_tmdb_results(
    search_client: TestClient, tmdb_mock: respx.MockRouter
) -> None:
    """Бек передає в TMDB правильні параметри і повертає фільми й серіали без персон."""
    route = tmdb_mock.get("/search/multi").respond(
        200,
        json={
            "page": 1,
            "results": [
                {
                    "media_type": "movie",
                    "id": 603,
                    "title": "Матриця",
                    "release_date": "1999-03-30",
                    "poster_path": "/matrix.jpg",
                },
                {
                    "media_type": "tv",
                    "id": 1396,
                    "name": "Пуститися берега",
                    "first_air_date": "2008-01-20",
                    "poster_path": None,
                },
                {"media_type": "person", "id": 6384, "name": "Кіану Рівз"},
            ],
        },
    )

    response = search_client.get("/api/search", params={"q": "  Матриця  "})

    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {
                "id": "603",
                "type": "movie",
                "title": "Матриця",
                "year": 1999,
                "poster": f"{IMAGE_BASE}/matrix.jpg",
            },
            {
                "id": "1396",
                "type": "series",
                "title": "Пуститися берега",
                "year": 2008,
                "poster": None,
            },
        ]
    }

    assert route.call_count == 1
    params = route.calls.last.request.url.params
    assert params["query"] == "Матриця"
    assert params["api_key"] == TMDB_TEST_KEY
    assert params["language"] == "uk-UA"
    assert params["include_adult"] == "false"


def test_search_tmdb_server_error_returns_503(
    search_client: TestClient, tmdb_mock: respx.MockRouter
) -> None:
    """Помилка TMDB (500) не пробивається назовні: користувач отримує 503."""
    tmdb_mock.get("/search/multi").respond(500, json={"status_message": "Internal error"})

    response = search_client.get("/api/search", params={"q": "Матриця"})

    assert response.status_code == 503
    assert response.json() == {"detail": UNAVAILABLE}


def test_search_tmdb_timeout_returns_503(
    search_client: TestClient, tmdb_mock: respx.MockRouter
) -> None:
    """Таймаут з'єднання з TMDB обробляється як недоступність пошуку (503)."""
    tmdb_mock.get("/search/multi").mock(side_effect=httpx.ConnectTimeout("timeout"))

    response = search_client.get("/api/search", params={"q": "Матриця"})

    assert response.status_code == 503
    assert response.json() == {"detail": UNAVAILABLE}
