"""Фікстури для тестів за тест-планом SCRUM-49."""

from collections.abc import Iterator
from uuid import uuid4

import pytest
import respx
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Connection
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db_session
from app.deps import get_current_user
from app.main import app
from app.models import User

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_TEST_KEY = "test-tmdb-key"
STEAM_HOST = "store.steampowered.com"
STEAM_SEARCH_PATH = "/api/storesearch/"


@pytest.fixture
def new_user() -> dict[str, str]:
    """Унікальні дані, щоб паралельні запуски CI не конфліктували в одній БД."""
    suffix = uuid4().hex[:10]
    return {
        "email": f"qa_{suffix}@example.com",
        "username": f"qa_{suffix}",
        "password": "goodpass1",
    }


@pytest.fixture
def client(db: Connection) -> Iterator[TestClient]:
    """Клієнт з тестовою БД; усі зміни відкочуються після тесту."""

    def override_session() -> Iterator[Session]:
        with Session(bind=db, join_transaction_mode="create_savepoint") as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def search_client() -> Iterator[TestClient]:
    """Клієнт для пошуку: авторизований користувач без БД і тестовий ключ TMDB."""
    settings = Settings(
        tmdb_api_key=SecretStr(TMDB_TEST_KEY),
        tmdb_base_url=TMDB_BASE_URL,
    )
    fake_user = User(
        id=uuid4(),
        email="search@example.com",
        username="search",
        password_hash="unused",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_current_user] = lambda: fake_user
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def tmdb_mock() -> Iterator[respx.MockRouter]:
    """Перехоплює всі httpx-запити до TMDB; справжня мережа не використовується.

    /api/search без type шукає ще й ігри у Steam Store API (SCRUM-58), тому
    Steam відповідає порожнім результатом: тести лишаються про TMDB.
    """
    with respx.mock(base_url=TMDB_BASE_URL, assert_all_called=True) as router:
        # host= робить маршрут абсолютним: base_url TMDB до нього не додається.
        router.route(host=STEAM_HOST, path=STEAM_SEARCH_PATH).respond(
            200, json={"total": 0, "items": []}
        )
        yield router
