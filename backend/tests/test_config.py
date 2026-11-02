from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from app.config import Settings
from app.database import create_database_engine

DATABASE_URL = "postgresql://demo:example-secret@localhost/mediatrack?sslmode=require"


@pytest.fixture(autouse=True)
def clear_database_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)


def test_blank_urls_allow_running_without_database() -> None:
    settings = Settings(_env_file=None, database_url=" ", test_database_url="")
    assert settings.database_url is None
    assert settings.test_database_url is None


def test_dotenv_and_environment_precedence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        f"DATABASE_URL={DATABASE_URL}\nTMDB_API_KEY=unused\nVITE_API_BASE_URL=/api\n",
        encoding="utf-8",
    )
    other_directory = tmp_path / "elsewhere"
    other_directory.mkdir()
    monkeypatch.chdir(other_directory)
    settings = Settings(_env_file=dotenv)
    assert settings.database_url.get_secret_value() == DATABASE_URL

    override = "postgresql://demo:override-secret@localhost/another_database"
    monkeypatch.setenv("DATABASE_URL", override)
    assert Settings(_env_file=dotenv).database_url.get_secret_value() == override


def test_settings_hide_credentials_in_repr_and_json() -> None:
    settings = Settings(_env_file=None, database_url=DATABASE_URL)
    assert "example-secret" not in repr(settings)
    assert "example-secret" not in settings.model_dump_json()


@pytest.mark.parametrize(
    "value",
    [
        "invalid-example-secret",
        "sqlite:///example-secret.db",
        "postgresql://demo:example-secret@localhost:not-a-port/database",
        "postgresql:///example-secret",
    ],
)
def test_invalid_urls_are_rejected_without_secret_in_error(value: str) -> None:
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, database_url=value)
    assert "example-secret" not in str(error.value)


def test_neon_connection_options_survive_driver_selection() -> None:
    database_url = SecretStr(
        DATABASE_URL + "&channel_binding=require&application_name=mediatrack"
    )
    engine = create_database_engine(database_url)
    try:
        assert engine.url.drivername == "postgresql+psycopg"
        assert engine.url.query["sslmode"] == "require"
        assert engine.url.query["channel_binding"] == "require"
        assert engine.url.query["application_name"] == "mediatrack"
    finally:
        engine.dispose()
