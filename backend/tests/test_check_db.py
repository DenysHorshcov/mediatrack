from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import OperationalError

from app import check_db
from app.config import Settings

DATABASE_URL = "postgresql://demo:example-secret@localhost/development"
TEST_DATABASE_URL = "postgresql://demo:test-secret@localhost/test"


def configure(
    monkeypatch: pytest.MonkeyPatch,
    database_url: str | None = DATABASE_URL,
    test_database_url: str | None = TEST_DATABASE_URL,
) -> MagicMock:
    settings = Settings(
        _env_file=None,
        database_url=database_url,
        test_database_url=test_database_url,
    )
    monkeypatch.setattr(check_db, "get_settings", lambda: settings)
    engine_factory = MagicMock()
    monkeypatch.setattr(check_db, "create_database_engine", engine_factory)
    return engine_factory


def test_test_connection_never_falls_back_to_development(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    engine_factory = configure(monkeypatch, test_database_url=None)
    assert check_db.main(["--test"]) == 1
    engine_factory.assert_not_called()
    assert "TEST_DATABASE_URL is not configured" in capsys.readouterr().err


def test_missing_development_connection_is_reported(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    engine_factory = configure(monkeypatch, database_url=None)
    assert check_db.main([]) == 1
    engine_factory.assert_not_called()
    assert "DATABASE_URL is not configured" in capsys.readouterr().err


def test_test_connection_selects_test_url_and_only_reads(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    engine_factory = configure(monkeypatch)
    connection = engine_factory.return_value.connect.return_value.__enter__.return_value
    connection.scalar.return_value = 1
    assert check_db.main(["--test"]) == 0
    assert engine_factory.call_args.args[0].get_secret_value() == TEST_DATABASE_URL
    assert str(connection.scalar.call_args.args[0]) == "SELECT 1"
    engine_factory.return_value.dispose.assert_called_once()
    assert "TEST_DATABASE_URL: PostgreSQL connection OK" in capsys.readouterr().out


def test_connection_failure_does_not_expose_driver_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    engine_factory = configure(monkeypatch)
    engine_factory.return_value.connect.side_effect = OperationalError(
        "SELECT 1", None, Exception(f"Connection failed: {DATABASE_URL}")
    )
    assert check_db.main([]) == 1
    engine_factory.return_value.dispose.assert_called_once()
    output = capsys.readouterr()
    assert "PostgreSQL connection failed" in output.err
    assert "example-secret" not in output.err + output.out


def test_invalid_config_is_reported_without_secret(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def invalid_settings() -> Settings:
        return Settings(_env_file=None, database_url="invalid-example-secret")

    monkeypatch.setattr(check_db, "get_settings", invalid_settings)
    assert check_db.main([]) == 1
    output = capsys.readouterr()
    assert "Invalid PostgreSQL configuration" in output.err
    assert "example-secret" not in output.err + output.out
