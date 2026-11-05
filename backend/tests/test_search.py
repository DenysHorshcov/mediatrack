from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection
from sqlalchemy.orm import Session

from app import rawg, tmdb
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


def _stub_tmdb(
    monkeypatch: pytest.MonkeyPatch, items: list[tmdb.SearchItem] | None = None
) -> None:
    async def fake(query: str, settings) -> list[tmdb.SearchItem]:
        return list(items or [])

    monkeypatch.setattr(tmdb, "search_titles", fake)


def _stub_rawg(
    monkeypatch: pytest.MonkeyPatch, items: list[tmdb.SearchItem] | None = None
) -> None:
    async def fake(query: str, settings) -> list[tmdb.SearchItem]:
        return list(items or [])

    monkeypatch.setattr(rawg, "search_games", fake)


def _stub_tmdb_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake(query: str, settings) -> list[tmdb.SearchItem]:
        raise tmdb.TMDBError("boom")

    monkeypatch.setattr(tmdb, "search_titles", fake)


def _stub_rawg_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake(query: str, settings) -> list[tmdb.SearchItem]:
        raise rawg.RAWGError("boom")

    monkeypatch.setattr(rawg, "search_games", fake)


MATRIX = tmdb.SearchItem(id="603", type="movie", title="Матриця", year=1999, poster=None)
BREAKING_BAD = tmdb.SearchItem(id="1396", type="series", title="Пуститися берега", year=2008)
WITCHER = tmdb.SearchItem(id="3328", type="game", title="The Witcher 3", year=2015)


def test_search_requires_auth(client: TestClient) -> None:
    assert client.get("/api/search?q=foo").status_code == 401


def test_search_requires_query(client: TestClient) -> None:
    _register(client)
    assert client.get("/api/search").status_code == 422


def test_search_default_mixes_titles_and_games(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_tmdb(monkeypatch, [MATRIX, BREAKING_BAD])
    _stub_rawg(monkeypatch, [WITCHER])
    _register(client)
    response = client.get("/api/search", params={"q": "matrix"})
    assert response.status_code == 200
    types = [item["type"] for item in response.json()["results"]]
    assert sorted(types) == ["game", "movie", "series"]


def test_search_type_game_returns_only_games(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_tmdb_error(monkeypatch)  # should not be called, but guard anyway
    _stub_rawg(monkeypatch, [WITCHER])
    _register(client)
    response = client.get("/api/search", params={"q": "witcher", "type": "game"})
    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 1
    assert body["results"][0]["type"] == "game"


def test_search_type_movie_filters_series_out(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_tmdb(monkeypatch, [MATRIX, BREAKING_BAD])
    _stub_rawg_error(monkeypatch)  # should not be called for type=movie
    _register(client)
    response = client.get("/api/search", params={"q": "matrix", "type": "movie"})
    assert response.status_code == 200
    body = response.json()
    assert [item["type"] for item in body["results"]] == ["movie"]


def test_search_rawg_error_does_not_break_titles(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_tmdb(monkeypatch, [MATRIX])
    _stub_rawg_error(monkeypatch)
    _register(client)
    response = client.get("/api/search", params={"q": "matrix"})
    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 1
    assert body["results"][0]["type"] == "movie"


def test_search_tmdb_error_does_not_break_games(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_tmdb_error(monkeypatch)
    _stub_rawg(monkeypatch, [WITCHER])
    _register(client)
    response = client.get("/api/search", params={"q": "witcher"})
    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 1
    assert body["results"][0]["type"] == "game"


def test_search_returns_503_when_both_providers_fail(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_tmdb_error(monkeypatch)
    _stub_rawg_error(monkeypatch)
    _register(client)
    response = client.get("/api/search", params={"q": "x"})
    assert response.status_code == 503
    assert "недоступний" in response.json()["detail"]


def test_search_rejects_unknown_type(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_tmdb(monkeypatch, [MATRIX])
    _stub_rawg(monkeypatch, [WITCHER])
    _register(client)
    response = client.get("/api/search", params={"q": "x", "type": "book"})
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
