"""Check the configured PostgreSQL connection without printing credentials."""

import argparse
import sys

from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import create_database_engine


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="store_true", help="Use TEST_DATABASE_URL only")
    args = parser.parse_args(argv)
    variable = "TEST_DATABASE_URL" if args.test else "DATABASE_URL"

    try:
        settings = get_settings()
    except ValidationError:
        print("Invalid PostgreSQL configuration. Check the URLs in .env.", file=sys.stderr)
        return 1

    database_url = settings.test_database_url if args.test else settings.database_url
    if database_url is None:
        print(f"{variable} is not configured in the root .env or environment.", file=sys.stderr)
        return 1

    try:
        engine = create_database_engine(database_url)
        try:
            with engine.connect() as connection:
                if connection.scalar(text("SELECT 1")) != 1:
                    print("Unexpected PostgreSQL response.", file=sys.stderr)
                    return 1
        finally:
            engine.dispose()
    except SQLAlchemyError:
        print(
            "PostgreSQL connection failed. Check the selected branch, credentials, "
            "SSL parameters and network access.",
            file=sys.stderr,
        )
        return 1

    print(f"{variable}: PostgreSQL connection OK (SELECT 1).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
