from argparse import Namespace
from io import StringIO
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from app.config import get_settings


def migration_config() -> Config:
    return Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))


def test_offline_migration_does_not_need_database_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "invalid-secret-must-not-be-printed")
    output = StringIO()
    config = migration_config()
    config.output_buffer = output
    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE users" in sql
    assert "CREATE TABLE watched_episodes" in sql
    assert "invalid-secret" not in sql


def test_invalid_database_selector_is_rejected_before_connecting() -> None:
    config = migration_config()
    config.cmd_opts = Namespace(x=["database=typo"])
    with pytest.raises(RuntimeError, match="database=test"):
        command.current(config)


def test_missing_test_url_never_falls_back_to_main_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_DATABASE_URL", "")
    config = migration_config()
    config.cmd_opts = Namespace(x=["database=test"])
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="TEST_DATABASE_URL is not configured"):
            command.current(config)
    finally:
        get_settings.cache_clear()
