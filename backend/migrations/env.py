from logging.config import fileConfig

from alembic import context
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import create_database_engine
from app.models import Base

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        dialect_name="postgresql",
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    target = context.get_x_argument(as_dictionary=True).get("database", "default")
    if target not in {"default", "test"}:
        raise RuntimeError("Use -x database=test or omit -x to select DATABASE_URL")
    try:
        settings = get_settings()
    except ValidationError:
        raise RuntimeError(
            "Invalid PostgreSQL configuration; check the root .env"
        ) from None
    database_url = (
        settings.test_database_url if target == "test" else settings.database_url
    )
    if database_url is None:
        variable = "TEST_DATABASE_URL" if target == "test" else "DATABASE_URL"
        raise RuntimeError(f"{variable} is not configured")

    engine = create_database_engine(database_url)
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                compare_server_default=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    except SQLAlchemyError:
        raise RuntimeError(
            "Migration failed; check database connectivity, permissions and schema compatibility"
        ) from None
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
