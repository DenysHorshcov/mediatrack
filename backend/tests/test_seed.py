import pytest
from argon2 import PasswordHasher
from sqlalchemy import func, select, update

from app.models import Episode, LibraryEntry, MediaTitle, Season, User, WatchedEpisode
from app.seed import seed_database, seed_id


@pytest.mark.database
def test_seed_is_repeatable_and_preserves_edits(db):
    password = "test-only-" + str(seed_id("test-password"))
    counts = seed_database(db, password)
    maximum_counts = {
        "users": 2,
        "media_titles": 3,
        "seasons": 1,
        "episodes": 3,
        "library_entries": 4,
        "watched_episodes": 2,
    }
    assert counts.keys() == maximum_counts.keys()
    assert all(0 <= count <= maximum_counts[table] for table, count in counts.items())
    original_hash = db.scalar(
        select(User.password_hash).where(User.id == seed_id("demo_olena"))
    )
    if counts["users"] == 2:
        assert PasswordHasher().verify(original_hash, password)
    entry_id = seed_id("demo_olena:series")
    db.execute(
        update(LibraryEntry)
        .where(LibraryEntry.id == entry_id)
        .values(status="dropped", rating=4)
    )
    db.execute(
        WatchedEpisode.__table__.delete().where(
            WatchedEpisode.library_entry_id == entry_id
        )
    )
    assert all(
        count == 0 for count in seed_database(db, "another-test-password").values()
    )
    assert (
        db.scalar(select(User.password_hash).where(User.id == seed_id("demo_olena")))
        == original_hash
    )
    assert db.execute(
        select(LibraryEntry.status, LibraryEntry.rating).where(
            LibraryEntry.id == entry_id
        )
    ).one() == ("dropped", 4)
    assert (
        db.scalar(
            select(func.count())
            .select_from(WatchedEpisode)
            .where(WatchedEpisode.library_entry_id == entry_id)
        )
        == 0
    )
    for model, keys in (
        (User, ("demo_olena", "demo_taras")),
        (MediaTitle, ("movie", "series", "game")),
        (Season, ("season",)),
        (Episode, ("episode-1", "episode-2", "episode-3")),
        (
            LibraryEntry,
            (
                "demo_olena:movie",
                "demo_olena:series",
                "demo_taras:series",
                "demo_taras:game",
            ),
        ),
    ):
        assert db.scalar(
            select(func.count())
            .select_from(model)
            .where(model.id.in_([seed_id(key) for key in keys]))
        ) == len(keys)


def test_seed_rejects_blank_password():
    with pytest.raises(ValueError, match="blank"):
        seed_database(None, "  ")
