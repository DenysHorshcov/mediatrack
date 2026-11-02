"""Explicit, repeatable development fixtures; no external catalog requests."""

import argparse
import getpass
import sys
from uuid import NAMESPACE_URL, UUID, uuid5

from argon2 import PasswordHasher
from pydantic import ValidationError
from sqlalchemy import Connection, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import create_database_engine
from app.models import Episode, LibraryEntry, MediaTitle, Season, User, WatchedEpisode


def seed_id(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"mediatrack:development-seed:v1:{name}")


def seed_database(connection: Connection, password: str) -> dict[str, int]:
    """Caller owns the transaction. Existing records are never updated."""
    if not password.strip():
        raise ValueError("Seed password must not be blank")
    counts: dict[str, int] = {}

    def add(model, key: str, **values) -> bool:
        table = model.__table__
        record_id = seed_id(key)
        statement = (
            insert(table)
            .values(id=record_id, **values)
            .on_conflict_do_nothing(index_elements=[table.c.id])
            .returning(table.c.id)
        )
        inserted = connection.execute(statement).scalar_one_or_none() is not None
        counts[table.name] = counts.get(table.name, 0) + int(inserted)
        return inserted

    hasher = PasswordHasher()
    for name in ("demo_olena", "demo_taras"):
        # Hash only new passwords, and leave existing hashes intact on reruns.
        if connection.scalar(select(User.id).where(User.id == seed_id(name))) is None:
            add(
                User,
                name,
                username=name,
                email=f"{name}@example.invalid",
                password_hash=hasher.hash(password),
            )
        else:
            counts.setdefault("users", 0)

    for kind, title in (
        ("movie", "Демо: Подорож до маяка"),
        ("series", "Демо: Місто історій"),
        ("game", "Демо: Острів пригод"),
    ):
        add(
            MediaTitle,
            kind,
            provider="rawg" if kind == "game" else "tmdb",
            external_id=f"seed-{kind}",
            media_type=kind,
            title=title,
            description="Вигаданий тайтл для локальної розробки, не запис провайдера.",
            description_language="uk",
        )
    add(
        Season, "season", title_id=seed_id("series"), season_number=1, name="Демо-сезон"
    )
    for number in (1, 2, 3):
        add(
            Episode,
            f"episode-{number}",
            season_id=seed_id("season"),
            episode_number=number,
            name=f"Демо-епізод {number}",
            runtime_minutes=40,
        )
    for username, kind, status, rating in (
        ("demo_olena", "movie", "planned", None),
        ("demo_olena", "series", "in_progress", 8),
        ("demo_taras", "series", "planned", None),
        ("demo_taras", "game", "on_hold", 7),
    ):
        name = f"{username}:{kind}"
        created = add(
            LibraryEntry,
            name,
            user_id=seed_id(username),
            title_id=seed_id(kind),
            status=status,
            rating=rating,
        )
        # Populate progress only for a new entry; reruns respect edited progress.
        if created and username == "demo_olena" and kind == "series":
            for number in (1, 3):
                connection.execute(
                    insert(WatchedEpisode).values(
                        library_entry_id=seed_id(name),
                        episode_id=seed_id(f"episode-{number}"),
                    )
                )
            counts["watched_episodes"] = 2
    counts.setdefault("watched_episodes", 0)
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add fictional MediaTrack development data"
    )
    parser.add_argument("--test", action="store_true", help="Use TEST_DATABASE_URL")
    args = parser.parse_args()
    variable = "TEST_DATABASE_URL" if args.test else "DATABASE_URL"
    try:
        settings = get_settings()
    except ValidationError:
        print(
            "Invalid database configuration; credentials are not printed",
            file=sys.stderr,
        )
        return 1
    url = settings.test_database_url if args.test else settings.database_url
    if url is None:
        print(f"{variable} is required", file=sys.stderr)
        return 1
    try:
        password = getpass.getpass("Password for demo_olena and demo_taras: ")
        if not password.strip() or password != getpass.getpass("Confirm password: "):
            print("Passwords must match and must not be blank", file=sys.stderr)
            return 1
    except EOFError, KeyboardInterrupt:
        print("Seed cancelled", file=sys.stderr)
        return 1
    engine = create_database_engine(url)
    try:
        with engine.begin() as connection:
            counts = seed_database(connection, password)
    except SQLAlchemyError:
        print(
            "Seed rolled back. Check connection and run Alembic migrations first; "
            "existing data may conflict with demo identities. Credentials are not printed.",
            file=sys.stderr,
        )
        return 1
    finally:
        engine.dispose()
    print(f"Seed complete ({variable}); inserted: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
