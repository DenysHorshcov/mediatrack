from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.main import app
from app.models import MediaTitle

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


REGISTER = {"email": "stats@example.com", "username": "statsuser", "password": "goodpass1"}


def _register(client: TestClient) -> None:
    assert client.post("/api/auth/register", json=REGISTER).status_code == 201


def _seed_title(
    db_conn: Connection,
    *,
    provider: str = "tmdb",
    media_type: str = "movie",
    external_id: str = "603",
    title: str = "Матриця",
) -> str:
    with Session(
        bind=db_conn, join_transaction_mode="create_savepoint"
    ) as session:
        row = MediaTitle(
            provider=provider,
            media_type=media_type,
            external_id=external_id,
            title=title,
            release_date=date(2000, 1, 1),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return str(row.id)


def test_stats_requires_auth(client: TestClient) -> None:
    assert client.get("/api/me/stats").status_code == 401


def test_stats_empty_user_returns_zeros(client: TestClient) -> None:
    _register(client)
    response = client.get("/api/me/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["by_type"] == {"movie": 0, "series": 0, "game": 0}
    assert body["by_status"] == {
        "planned": 0,
        "in_progress": 0,
        "completed": 0,
        "on_hold": 0,
        "dropped": 0,
    }
    assert body["average_rating"] is None
    assert body["completed_this_year"] == 0


def test_stats_counts_by_type_and_status(client: TestClient, db: Connection) -> None:
    _register(client)
    movie = _seed_title(db, external_id="603")
    series = _seed_title(db, media_type="series", external_id="1396", title="BB")
    game = _seed_title(
        db, provider="rawg", media_type="game", external_id="3328", title="Witcher 3"
    )

    client.put(f"/api/me/titles/{movie}", json={"status": "completed"})
    client.put(f"/api/me/titles/{series}", json={"status": "in_progress"})
    client.put(f"/api/me/titles/{game}", json={"status": "planned"})

    body = client.get("/api/me/stats").json()
    assert body["total"] == 3
    assert body["by_type"] == {"movie": 1, "series": 1, "game": 1}
    assert body["by_status"]["completed"] == 1
    assert body["by_status"]["in_progress"] == 1
    assert body["by_status"]["planned"] == 1


def test_stats_computes_average_rating(client: TestClient, db: Connection) -> None:
    _register(client)
    a = _seed_title(db, external_id="603")
    b = _seed_title(db, external_id="604", title="Друге")
    c = _seed_title(db, external_id="605", title="Третє")

    client.patch(f"/api/me/titles/{a}", json={"rating": 7})
    client.patch(f"/api/me/titles/{b}", json={"rating": 8})
    client.patch(f"/api/me/titles/{c}", json={"rating": 10})

    body = client.get("/api/me/stats").json()
    assert body["average_rating"] == pytest.approx(8.3, abs=0.1)


def test_stats_completed_this_year_counts_only_current_year(
    client: TestClient, db: Connection
) -> None:
    _register(client)
    title_id = _seed_title(db)
    client.put(f"/api/me/titles/{title_id}", json={"status": "completed"})
    body = client.get("/api/me/stats").json()
    assert body["completed_this_year"] == 1


def test_stats_average_rating_ignores_null_ratings(
    client: TestClient, db: Connection
) -> None:
    _register(client)
    rated = _seed_title(db, external_id="603")
    unrated = _seed_title(db, external_id="604", title="Без оцінки")
    client.patch(f"/api/me/titles/{rated}", json={"rating": 9})
    client.put(f"/api/me/titles/{unrated}", json={"status": "planned"})
    body = client.get("/api/me/stats").json()
    assert body["average_rating"] == 9.0
    assert body["total"] == 2
