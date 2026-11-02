from collections.abc import Iterator
from functools import lru_cache

from pydantic import SecretStr
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


def create_database_engine(database_url: SecretStr) -> Engine:
    url = make_url(database_url.get_secret_value()).set(drivername="postgresql+psycopg")
    return create_engine(
        url,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"connect_timeout": 10},
    )


@lru_cache
def get_engine() -> Engine:
    database_url = get_settings().database_url
    if database_url is None:
        raise RuntimeError("DATABASE_URL is not configured")
    return create_database_engine(database_url)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db_session() -> Iterator[Session]:
    """Provide a request-scoped session; services own begin/commit/rollback."""
    with get_session_factory()() as session:
        yield session
