from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import Connection, delete, func, insert, select
from sqlalchemy.exc import IntegrityError

from app.models import Episode, LibraryEntry, MediaTitle, Season, User, WatchedEpisode

pytestmark = pytest.mark.database


def add_user(db: Connection, **overrides):
    token = uuid4().hex
    values = {
        "email": f"{token}@example.invalid",
        "username": f"user_{token}",
        "password_hash": "test-only-placeholder",
    }
    values.update(overrides)
    return db.scalar(insert(User).values(**values).returning(User.id))


def add_title(db: Connection, **overrides):
    values = {
        "provider": "tmdb",
        "media_type": "series",
        "external_id": uuid4().hex,
        "title": "Test series",
    }
    values.update(overrides)
    return db.scalar(insert(MediaTitle).values(**values).returning(MediaTitle.id))


def rejects(db: Connection, statement) -> None:
    with pytest.raises(IntegrityError), db.begin_nested():
        db.execute(statement)


def test_defaults_are_generated_by_postgresql(db: Connection) -> None:
    user_id = add_user(db)
    title_id = add_title(db)
    entry = (
        db.execute(
            insert(LibraryEntry)
            .values(user_id=user_id, title_id=title_id)
            .returning(LibraryEntry.__table__)
        )
        .mappings()
        .one()
    )
    assert entry["id"] is not None
    assert entry["status"] == "planned"
    assert entry["rating"] is None and entry["review_text"] is None
    assert entry["created_at"].tzinfo is not None
    assert db.scalar(select(User.avatar_url).where(User.id == user_id)) is None


@pytest.mark.parametrize("field", ["email", "username"])
def test_user_identity_is_unique_ignoring_case(db: Connection, field: str) -> None:
    token = uuid4().hex
    original = f"{token}@example.invalid" if field == "email" else f"u_{token}"
    add_user(db, **{field: original})
    values = {
        "email": f"{uuid4().hex}@example.invalid",
        "username": f"u_{uuid4().hex}",
        "password_hash": "test-only-placeholder",
    }
    values[field] = original.upper()
    rejects(db, insert(User).values(**values))


def test_external_identity_includes_media_type(db: Connection) -> None:
    external_id = uuid4().hex
    add_title(db, external_id=external_id, media_type="movie")
    add_title(db, external_id=external_id, media_type="series")
    rejects(
        db,
        insert(MediaTitle).values(
            provider="tmdb",
            media_type="movie",
            external_id=external_id,
            title="Duplicate",
        ),
    )


@pytest.mark.parametrize(
    "provider,media_type", [("rawg", "movie"), ("tmdb", "game"), ("other", "series")]
)
def test_provider_and_media_type_must_match(
    db: Connection, provider: str, media_type: str
) -> None:
    rejects(
        db,
        insert(MediaTitle).values(
            provider=provider,
            media_type=media_type,
            external_id=uuid4().hex,
            title="Invalid",
        ),
    )


@pytest.mark.parametrize(
    "description,language",
    [("Description", None), (None, "uk"), ("Description", "fr"), (" ", "en")],
)
def test_description_and_language_are_consistent(
    db: Connection, description, language
) -> None:
    rejects(
        db,
        insert(MediaTitle).values(
            provider="tmdb",
            media_type="movie",
            external_id=uuid4().hex,
            title="Test",
            description=description,
            description_language=language,
        ),
    )


@pytest.mark.parametrize("rating", [0, 11, -1])
def test_rating_range(db: Connection, rating: int) -> None:
    rejects(
        db,
        insert(LibraryEntry).values(
            user_id=add_user(db), title_id=add_title(db), rating=rating
        ),
    )


def test_invalid_status_and_missing_foreign_keys(db: Connection) -> None:
    user_id, title_id = add_user(db), add_title(db)
    rejects(
        db,
        insert(LibraryEntry).values(
            user_id=user_id, title_id=title_id, status="unknown"
        ),
    )
    rejects(db, insert(LibraryEntry).values(user_id=uuid4(), title_id=title_id))
    rejects(db, insert(LibraryEntry).values(user_id=user_id, title_id=uuid4()))


def test_one_library_entry_per_user_and_title(db: Connection) -> None:
    user_id, title_id = add_user(db), add_title(db)
    db.execute(insert(LibraryEntry).values(user_id=user_id, title_id=title_id))
    rejects(db, insert(LibraryEntry).values(user_id=user_id, title_id=title_id))


def test_episode_numbers_and_uniqueness(db: Connection) -> None:
    title_id = add_title(db)
    season_id = db.scalar(
        insert(Season).values(title_id=title_id, season_number=0).returning(Season.id)
    )
    rejects(db, insert(Season).values(title_id=title_id, season_number=-1))
    rejects(db, insert(Season).values(title_id=title_id, season_number=0))
    db.execute(insert(Episode).values(season_id=season_id, episode_number=1))
    rejects(db, insert(Episode).values(season_id=season_id, episode_number=1))
    rejects(db, insert(Episode).values(season_id=season_id, episode_number=0))
    rejects(
        db,
        insert(Episode).values(
            season_id=season_id, episode_number=2, runtime_minutes=0
        ),
    )


def test_library_removal_deletes_only_owners_review_and_progress(
    db: Connection,
) -> None:
    owner, other_owner, title = add_user(db), add_user(db), add_title(db)
    review_time = datetime.now(UTC)
    entry = db.scalar(
        insert(LibraryEntry)
        .values(
            user_id=owner,
            title_id=title,
            review_text="Owner review",
            review_updated_at=review_time,
        )
        .returning(LibraryEntry.id)
    )
    other_entry = db.scalar(
        insert(LibraryEntry)
        .values(
            user_id=other_owner,
            title_id=title,
            review_text="Other review",
            review_updated_at=review_time,
        )
        .returning(LibraryEntry.id)
    )
    season = db.scalar(
        insert(Season).values(title_id=title, season_number=1).returning(Season.id)
    )
    episode = db.scalar(
        insert(Episode).values(season_id=season, episode_number=1).returning(Episode.id)
    )
    db.execute(
        insert(WatchedEpisode).values(library_entry_id=entry, episode_id=episode)
    )
    db.execute(
        insert(WatchedEpisode).values(library_entry_id=other_entry, episode_id=episode)
    )
    rejects(
        db, insert(WatchedEpisode).values(library_entry_id=entry, episode_id=episode)
    )
    rejects(db, delete(MediaTitle).where(MediaTitle.id == title))

    db.execute(delete(LibraryEntry).where(LibraryEntry.id == entry))
    assert db.scalar(select(LibraryEntry.id).where(LibraryEntry.id == entry)) is None
    assert (
        db.scalar(
            select(func.count())
            .select_from(WatchedEpisode)
            .where(WatchedEpisode.library_entry_id == entry)
        )
        == 0
    )
    assert (
        db.scalar(
            select(LibraryEntry.review_text).where(LibraryEntry.id == other_entry)
        )
        == "Other review"
    )
    assert (
        db.scalar(
            select(func.count())
            .select_from(WatchedEpisode)
            .where(WatchedEpisode.library_entry_id == other_entry)
        )
        == 1
    )
    assert db.scalar(select(MediaTitle.id).where(MediaTitle.id == title)) == title

    db.execute(delete(User).where(User.id == other_owner))
    assert (
        db.scalar(select(LibraryEntry.id).where(LibraryEntry.id == other_entry)) is None
    )
    assert (
        db.scalar(
            select(func.count())
            .select_from(WatchedEpisode)
            .where(WatchedEpisode.library_entry_id == other_entry)
        )
        == 0
    )
