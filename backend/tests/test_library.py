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


REGISTER = {"email": "lib@example.com", "username": "libuser", "password": "goodpass1"}


def _register(client: TestClient) -> None:
    assert client.post("/api/auth/register", json=REGISTER).status_code == 201


def _seed_title(
    db: Session,
    *,
    provider: str = "tmdb",
    media_type: str = "movie",
    external_id: str = "603",
    title: str = "Матриця",
    release_date: date | None = date(1999, 3, 31),
) -> MediaTitle:
    row = MediaTitle(
        provider=provider,
        media_type=media_type,
        external_id=external_id,
        title=title,
        release_date=release_date,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _title_in_connection(db_conn: Connection, **kwargs) -> str:
    """Create a title in the same transaction the test client sees."""
    with Session(
        bind=db_conn, join_transaction_mode="create_savepoint"
    ) as session:
        row = _seed_title(session, **kwargs)
        return str(row.id)


def test_put_requires_auth(client: TestClient) -> None:
    assert client.put("/api/me/titles/00000000-0000-0000-0000-000000000000", json={"status": "planned"}).status_code == 401


def test_put_rejects_unknown_status(client: TestClient, db: Connection) -> None:
    _register(client)
    title_id = _title_in_connection(db)
    response = client.put(f"/api/me/titles/{title_id}", json={"status": "nope"})
    assert response.status_code == 422
    assert response.json()["fields"]["status"]


def test_put_creates_entry_and_get_returns_it(
    client: TestClient, db: Connection
) -> None:
    _register(client)
    title_id = _title_in_connection(db)
    response = client.put(
        f"/api/me/titles/{title_id}", json={"status": "in_progress"}
    )
    assert response.status_code == 200
    body = response.json()["entry"]
    assert body["id"] == title_id
    assert body["status"] == "in_progress"
    assert body["title"] == "Матриця"
    assert body["year"] == 1999

    get_response = client.get(f"/api/me/titles/{title_id}")
    assert get_response.status_code == 200
    assert get_response.json()["entry"]["status"] == "in_progress"


def test_put_updates_existing_entry(client: TestClient, db: Connection) -> None:
    _register(client)
    title_id = _title_in_connection(db)
    client.put(f"/api/me/titles/{title_id}", json={"status": "planned"})
    response = client.put(
        f"/api/me/titles/{title_id}", json={"status": "completed"}
    )
    assert response.status_code == 200
    assert response.json()["entry"]["status"] == "completed"


def test_put_returns_404_for_unknown_title(client: TestClient) -> None:
    _register(client)
    response = client.put(
        "/api/me/titles/00000000-0000-0000-0000-000000000000",
        json={"status": "planned"},
    )
    assert response.status_code == 404


def test_delete_removes_entry(client: TestClient, db: Connection) -> None:
    _register(client)
    title_id = _title_in_connection(db)
    client.put(f"/api/me/titles/{title_id}", json={"status": "planned"})
    delete_response = client.delete(f"/api/me/titles/{title_id}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/me/titles/{title_id}").status_code == 404


def test_delete_is_idempotent(client: TestClient) -> None:
    _register(client)
    response = client.delete("/api/me/titles/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 204


def test_get_entry_returns_404_when_no_entry(
    client: TestClient, db: Connection
) -> None:
    _register(client)
    title_id = _title_in_connection(db)
    assert client.get(f"/api/me/titles/{title_id}").status_code == 404


def test_list_filters_by_status_and_type(
    client: TestClient, db: Connection
) -> None:
    _register(client)
    movie_id = _title_in_connection(db, external_id="603")
    series_id = _title_in_connection(
        db, external_id="1396", media_type="series", title="Пуститися берега"
    )
    game_id = _title_in_connection(
        db, provider="rawg", media_type="game", external_id="3328", title="Witcher 3"
    )

    client.put(f"/api/me/titles/{movie_id}", json={"status": "completed"})
    client.put(f"/api/me/titles/{series_id}", json={"status": "in_progress"})
    client.put(f"/api/me/titles/{game_id}", json={"status": "planned"})

    all_items = client.get("/api/me/titles").json()["items"]
    assert len(all_items) == 3

    only_completed = client.get("/api/me/titles?status=completed").json()["items"]
    assert [item["id"] for item in only_completed] == [movie_id]

    only_games = client.get("/api/me/titles?type=game").json()["items"]
    assert [item["id"] for item in only_games] == [game_id]

    completed_games = client.get(
        "/api/me/titles?status=completed&type=game"
    ).json()["items"]
    assert completed_games == []


def test_list_rejects_invalid_filter(client: TestClient) -> None:
    _register(client)
    assert client.get("/api/me/titles?status=bogus").status_code == 422
    assert client.get("/api/me/titles?type=book").status_code == 422


def test_patch_requires_auth(client: TestClient) -> None:
    assert client.patch(
        "/api/me/titles/00000000-0000-0000-0000-000000000000",
        json={"rating": 8},
    ).status_code == 401


def test_patch_rejects_out_of_range(client: TestClient, db: Connection) -> None:
    _register(client)
    title_id = _title_in_connection(db)
    client.put(f"/api/me/titles/{title_id}", json={"status": "planned"})
    for bad in (0, 11, -1):
        response = client.patch(f"/api/me/titles/{title_id}", json={"rating": bad})
        assert response.status_code == 422
        assert response.json()["fields"]["rating"]


def test_patch_rejects_extra_fields(client: TestClient, db: Connection) -> None:
    _register(client)
    title_id = _title_in_connection(db)
    client.put(f"/api/me/titles/{title_id}", json={"status": "planned"})
    response = client.patch(
        f"/api/me/titles/{title_id}", json={"rating": 8, "status": "completed"}
    )
    assert response.status_code == 422


def test_patch_creates_entry_with_completed_status(
    client: TestClient, db: Connection
) -> None:
    _register(client)
    title_id = _title_in_connection(db)
    response = client.patch(f"/api/me/titles/{title_id}", json={"rating": 9})
    assert response.status_code == 200
    body = response.json()["entry"]
    assert body["rating"] == 9
    assert body["status"] == "completed"


def test_patch_updates_rating_on_existing_entry(
    client: TestClient, db: Connection
) -> None:
    _register(client)
    title_id = _title_in_connection(db)
    client.put(f"/api/me/titles/{title_id}", json={"status": "in_progress"})
    response = client.patch(f"/api/me/titles/{title_id}", json={"rating": 7})
    assert response.status_code == 200
    body = response.json()["entry"]
    assert body["status"] == "in_progress"  # status preserved
    assert body["rating"] == 7


def test_patch_clears_rating(client: TestClient, db: Connection) -> None:
    _register(client)
    title_id = _title_in_connection(db)
    client.patch(f"/api/me/titles/{title_id}", json={"rating": 5})
    response = client.patch(f"/api/me/titles/{title_id}", json={"rating": None})
    assert response.status_code == 200
    assert response.json()["entry"]["rating"] is None


def test_patch_clear_without_entry_returns_404(
    client: TestClient, db: Connection
) -> None:
    _register(client)
    title_id = _title_in_connection(db)
    response = client.patch(f"/api/me/titles/{title_id}", json={"rating": None})
    assert response.status_code == 404


def test_patch_returns_404_for_unknown_title(client: TestClient) -> None:
    _register(client)
    response = client.patch(
        "/api/me/titles/00000000-0000-0000-0000-000000000000",
        json={"rating": 5},
    )
    assert response.status_code == 404


def test_list_returns_rating(client: TestClient, db: Connection) -> None:
    _register(client)
    title_id = _title_in_connection(db)
    client.patch(f"/api/me/titles/{title_id}", json={"rating": 6})
    items = client.get("/api/me/titles").json()["items"]
    assert items[0]["rating"] == 6
    assert items[0]["status"] == "completed"
