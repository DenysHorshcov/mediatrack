from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection
from sqlalchemy.orm import Session

from app import tmdb
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


REGISTER = {"email": "searcher@example.com", "username": "searcher", "password": "goodpass1"}


def _register(client: TestClient) -> None:
    assert client.post("/api/auth/register", json=REGISTER).status_code == 201


def test_search_requires_auth(client: TestClient) -> None:
    assert client.get("/api/search?q=foo").status_code == 401


def test_search_returns_mapped_results(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake(query: str, settings) -> list[tmdb.SearchItem]:
        assert query == "матриця"
        return [
            tmdb.SearchItem(
                id="603",
                type="movie",
                title="Матриця",
                year=1999,
                poster="https://image.tmdb.org/t/p/w342/matrix.jpg",
            ),
            tmdb.SearchItem(
                id="1396",
                type="series",
                title="Пуститися берега",
                year=2008,
                poster=None,
            ),
        ]

    monkeypatch.setattr(tmdb, "search_titles", fake)
    _register(client)
    response = client.get("/api/search", params={"q": "матриця"})
    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 2
    assert body["results"][0]["type"] == "movie"
    assert body["results"][1]["type"] == "series"


def test_search_handles_tmdb_error_as_503(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake(query: str, settings) -> list[tmdb.SearchItem]:
        raise tmdb.TMDBError("boom")

    monkeypatch.setattr(tmdb, "search_titles", fake)
    _register(client)
    response = client.get("/api/search", params={"q": "x"})
    assert response.status_code == 503
    assert "недоступний" in response.json()["detail"]


def test_search_requires_query(client: TestClient) -> None:
    _register(client)
    response = client.get("/api/search")
    assert response.status_code == 422


def test_tmdb_mapping_filters_people_and_blank_titles() -> None:
    base = "https://image.tmdb.org/t/p/w342"
    assert tmdb._map_item({"media_type": "person", "id": 1, "name": "A"}, base) is None
    assert tmdb._map_item({"media_type": "movie", "id": 1}, base) is None
    assert tmdb._map_item({"media_type": "tv", "id": 1, "name": ""}, base) is None

    movie = tmdb._map_item(
        {
            "media_type": "movie",
            "id": 10,
            "title": "Фільм",
            "release_date": "2020-01-02",
            "poster_path": "/p.jpg",
        },
        base,
    )
    assert movie is not None
    assert movie.type == "movie"
    assert movie.year == 2020
    assert movie.poster == f"{base}/p.jpg"

    series = tmdb._map_item(
        {
            "media_type": "tv",
            "id": 20,
            "name": "Серіал",
            "first_air_date": "",
        },
        base,
    )
    assert series is not None
    assert series.type == "series"
    assert series.year is None
    assert series.poster is None
