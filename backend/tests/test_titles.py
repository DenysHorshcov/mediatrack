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


REGISTER = {"email": "titles@example.com", "username": "titlesuser", "password": "goodpass1"}


def _register(client: TestClient) -> None:
    assert client.post("/api/auth/register", json=REGISTER).status_code == 201


MATRIX_DETAILS = tmdb.TitleDetails(
    title="Матриця",
    original_title="The Matrix",
    description="Нео дізнається про Матрицю.",
    description_language="uk",
    poster_url="https://image.tmdb.org/t/p/w342/matrix.jpg",
    release_date="1999-03-31",
    genres=["Бойовик", "Фантастика"],
    seasons_count=None,
)

BREAKING_BAD_DETAILS = tmdb.TitleDetails(
    title="Пуститися берега",
    original_title="Breaking Bad",
    description="Учитель хімії стає на шлях злочину.",
    description_language="uk",
    poster_url=None,
    release_date="2008-01-20",
    genres=["Драма", "Кримінал"],
    seasons_count=5,
)

WITCHER_DETAILS = tmdb.TitleDetails(
    title="The Witcher 3",
    original_title=None,
    description="Open world RPG.",
    description_language="en",
    poster_url="https://media.rawg.io/w3.jpg",
    release_date="2015-05-18",
    genres=["RPG", "Adventure"],
    seasons_count=None,
)


def test_get_title_requires_auth(client: TestClient) -> None:
    response = client.get("/api/titles/tmdb/movie/603")
    assert response.status_code == 401


def test_get_title_fetches_and_persists_tmdb_movie(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, str]] = []

    async def fake(media_type: str, external_id: str, settings) -> tmdb.TitleDetails:
        calls.append((media_type, external_id))
        return MATRIX_DETAILS

    monkeypatch.setattr(tmdb, "fetch_title_details", fake)
    _register(client)

    response = client.get("/api/titles/tmdb/movie/603")
    assert response.status_code == 200
    body = response.json()["title"]
    assert body["title"] == "Матриця"
    assert body["year"] == 1999
    assert body["genres"] == ["Бойовик", "Фантастика"]
    assert body["seasons_count"] is None
    assert body["description_language"] == "uk"

    # Second call hits the DB cache, provider is not invoked again.
    response2 = client.get("/api/titles/tmdb/movie/603")
    assert response2.status_code == 200
    assert response2.json()["title"]["title"] == "Матриця"
    assert len(calls) == 1


def test_get_title_returns_seasons_count_for_series(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake(media_type: str, external_id: str, settings) -> tmdb.TitleDetails:
        return BREAKING_BAD_DETAILS

    monkeypatch.setattr(tmdb, "fetch_title_details", fake)
    _register(client)

    response = client.get("/api/titles/tmdb/series/1396")
    assert response.status_code == 200
    body = response.json()["title"]
    assert body["media_type"] == "series"
    assert body["seasons_count"] == 5


def test_get_title_uses_rawg_for_games(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake(external_id: str, settings) -> tmdb.TitleDetails:
        return WITCHER_DETAILS

    monkeypatch.setattr(rawg, "fetch_game_details", fake)
    _register(client)

    response = client.get("/api/titles/rawg/game/3328")
    assert response.status_code == 200
    body = response.json()["title"]
    assert body["title"] == "The Witcher 3"
    assert body["description_language"] == "en"
    assert body["genres"] == ["RPG", "Adventure"]
    assert body["seasons_count"] is None


def test_get_title_rejects_invalid_provider_type_pair(client: TestClient) -> None:
    _register(client)
    assert client.get("/api/titles/tmdb/game/1").status_code == 404
    assert client.get("/api/titles/rawg/movie/1").status_code == 404
    assert client.get("/api/titles/other/movie/1").status_code == 404


def test_get_title_returns_404_when_provider_has_no_such_title(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake(media_type: str, external_id: str, settings) -> tmdb.TitleDetails:
        raise tmdb.TMDBError("not found")

    monkeypatch.setattr(tmdb, "fetch_title_details", fake)
    _register(client)
    assert client.get("/api/titles/tmdb/movie/9999999").status_code == 404
