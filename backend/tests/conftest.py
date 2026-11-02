from collections.abc import Iterator

import pytest
from sqlalchemy import Connection, Engine, inspect
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings
from app.database import create_database_engine
from app.models import Base


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--database-tests",
        action="store_true",
        default=False,
        help="Run PostgreSQL integration tests using TEST_DATABASE_URL",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if not config.getoption("--database-tests"):
        for item in items:
            if "database" in item.keywords:
                item.add_marker(
                    pytest.mark.skip(
                        reason="Use --database-tests with a separate test database"
                    )
                )


@pytest.fixture(scope="session")
def database_engine() -> Iterator[Engine]:
    settings = Settings()
    if settings.test_database_url is None:
        raise pytest.UsageError("TEST_DATABASE_URL is required for --database-tests")
    test_url = make_url(settings.test_database_url.get_secret_value())
    if settings.database_url is not None:
        app_url = make_url(settings.database_url.get_secret_value())

        def identity(url: URL) -> tuple[str, int, str | None]:
            return (
                url.host.lower().replace("-pooler.", "."),
                url.port or 5432,
                url.database,
            )

        if identity(test_url) == identity(app_url):
            raise pytest.UsageError(
                "TEST_DATABASE_URL must point to a different database from DATABASE_URL"
            )
    engine = create_database_engine(settings.test_database_url)
    try:
        try:
            tables = set(inspect(engine).get_table_names())
        except SQLAlchemyError:
            raise pytest.UsageError(
                "Cannot connect to the test database; credentials are not printed"
            ) from None
        if not set(Base.metadata.tables).issubset(tables):
            raise pytest.UsageError(
                "Apply Alembic migrations to the test database before --database-tests"
            )
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db(database_engine: Engine) -> Iterator[Connection]:
    with database_engine.connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()
