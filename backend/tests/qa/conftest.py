"""Фікстури для QA-тестів за тест-планом SCRUM-49 (SCRUM-68, SCRUM-69)."""

import random
from collections.abc import Callable, Iterator
from datetime import date
from uuid import UUID, uuid4

import pytest
import respx
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Connection, insert
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db_session
from app.deps import get_current_user
from app.main import app
from app.models import MediaTitle, User

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_TEST_KEY = "test-tmdb-key"
STEAM_HOST = "store.steampowered.com"
STEAM_SEARCH_PATH = "/api/storesearch/"
STEAM_API_URL = f"https://{STEAM_HOST}/api"


def _test_settings() -> Settings:
    return Settings(
        tmdb_api_key=SecretStr(TMDB_TEST_KEY),
        tmdb_base_url=TMDB_BASE_URL,
        rawg_base_url=STEAM_API_URL,
    )


def random_external_id() -> str:
    """Числовий id, що не перетинається між тестами і паралельними запусками CI."""
    return str(random.randint(10**8, 10**9))


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
    settings = _test_settings()
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


@pytest.fixture
def api_client(db: Connection) -> Iterator[TestClient]:
    """Клієнт з тестовою БД, справжньою авторизацією і тестовими ключами TMDB/Steam."""
    settings = _test_settings()

    def override_session() -> Iterator[Session]:
        with Session(bind=db, join_transaction_mode="create_savepoint") as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def external_api() -> Iterator[respx.MockRouter]:
    """Заглушка для всіх зовнішніх HTTP-запитів (TMDB і Steam).

    Маршрути тест додає сам. Будь-який незамоканий запит падає з
    AllMockedAssertionError, тож справжня мережа ніколи не використовується.
    """
    with respx.mock(assert_all_called=False) as router:
        yield router


@pytest.fixture
def register(api_client: TestClient) -> Callable[[], dict]:
    """Реєструє нового унікального користувача і логінить клієнт під ним."""

    def _register() -> dict:
        suffix = uuid4().hex[:10]
        body = {
            "email": f"qa_{suffix}@example.com",
            "username": f"qa_{suffix}",
            "password": "goodpass1",
        }
        api_client.cookies.clear()
        response = api_client.post("/api/auth/register", json=body)
        assert response.status_code == 201
        return response.json()["user"]

    return _register


@pytest.fixture
def make_title(db: Connection) -> Callable[..., UUID]:
    """Створює тайтл у media_titles (відкочується разом з тестом)."""

    def _make(
        media_type: str = "movie",
        title: str = "Тестовий тайтл",
        external_id: str | None = None,
    ) -> UUID:
        provider = "rawg" if media_type == "game" else "tmdb"
        return db.execute(
            insert(MediaTitle)
            .values(
                provider=provider,
                media_type=media_type,
                external_id=external_id or random_external_id(),
                title=title,
                release_date=date(2020, 1, 1),
            )
            .returning(MediaTitle.id)
        ).scalar_one()

    return _make
