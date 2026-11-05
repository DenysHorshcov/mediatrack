"""Shared catalog metadata and private library records."""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    MetaData,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s_%(column_1_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class UUIDPrimaryKey:
    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(254))
    username: Mapped[str] = mapped_column(String(50))
    password_hash: Mapped[str] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("uq_users_email_lower", func.lower(email), unique=True),
        Index("uq_users_username_lower", func.lower(username), unique=True),
        CheckConstraint(
            "email = btrim(email) AND length(email) > 0", name="email_trimmed"
        ),
        CheckConstraint(
            "username = btrim(username) AND length(username) > 0",
            name="username_trimmed",
        ),
        CheckConstraint(
            "length(btrim(password_hash)) > 0", name="password_hash_not_blank"
        ),
    )


class MediaTitle(UUIDPrimaryKey, Base):
    __tablename__ = "media_titles"

    provider: Mapped[str] = mapped_column(String(10))
    external_id: Mapped[str] = mapped_column(Text)
    media_type: Mapped[str] = mapped_column(String(10))
    title: Mapped[str] = mapped_column(Text)
    original_title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    description_language: Mapped[str | None] = mapped_column(String(10))
    poster_url: Mapped[str | None] = mapped_column(Text)
    release_date: Mapped[date | None]
    genres: Mapped[str | None] = mapped_column(Text)
    seasons_count: Mapped[int | None]
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "media_type",
            "external_id",
            name="uq_media_titles_external_identity",
        ),
        CheckConstraint(
            "(provider = 'tmdb' AND media_type IN ('movie', 'series')) "
            "OR (provider = 'rawg' AND media_type = 'game')",
            name="provider_media_type",
        ),
        CheckConstraint(
            "title = btrim(title) AND length(title) > 0", name="title_trimmed"
        ),
        CheckConstraint(
            "external_id = btrim(external_id) AND length(external_id) > 0",
            name="external_id_trimmed",
        ),
        CheckConstraint(
            "(description IS NULL AND description_language IS NULL) OR "
            "(description IS NOT NULL AND description_language IS NOT NULL "
            "AND description_language IN ('uk', 'en') AND length(btrim(description)) > 0)",
            name="description_language",
        ),
    )


class LibraryEntry(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "library_entries"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title_id: Mapped[UUID] = mapped_column(
        ForeignKey("media_titles.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(20), server_default=text("'planned'"))
    rating: Mapped[int | None] = mapped_column(SmallInteger)
    review_text: Mapped[str | None] = mapped_column(Text)
    review_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("user_id", "title_id"),
        Index("ix_library_entries_title_id", "title_id"),
        CheckConstraint(
            "rating IS NULL OR rating BETWEEN 1 AND 10", name="rating_range"
        ),
        CheckConstraint(
            "status IN ('planned', 'in_progress', 'completed', 'on_hold', 'dropped')",
            name="status_values",
        ),
    )


class Season(UUIDPrimaryKey, Base):
    __tablename__ = "seasons"

    title_id: Mapped[UUID] = mapped_column(
        ForeignKey("media_titles.id", ondelete="CASCADE")
    )
    season_number: Mapped[int]
    name: Mapped[str | None] = mapped_column(Text)
    air_date: Mapped[date | None]
    episodes_fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    __table_args__ = (
        UniqueConstraint("title_id", "season_number"),
        CheckConstraint("season_number >= 0", name="season_number_range"),
    )


class Episode(UUIDPrimaryKey, Base):
    __tablename__ = "episodes"

    season_id: Mapped[UUID] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE")
    )
    episode_number: Mapped[int]
    name: Mapped[str | None] = mapped_column(Text)
    air_date: Mapped[date | None]
    runtime_minutes: Mapped[int | None]

    __table_args__ = (
        UniqueConstraint("season_id", "episode_number"),
        CheckConstraint("episode_number >= 1", name="episode_number_range"),
        CheckConstraint(
            "runtime_minutes IS NULL OR runtime_minutes > 0", name="runtime_positive"
        ),
    )


class WatchedEpisode(Base):
    __tablename__ = "watched_episodes"

    library_entry_id: Mapped[UUID] = mapped_column(
        ForeignKey("library_entries.id", ondelete="CASCADE"), primary_key=True
    )
    episode_id: Mapped[UUID] = mapped_column(
        ForeignKey("episodes.id", ondelete="CASCADE"), primary_key=True
    )
    watched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("ix_watched_episodes_episode_id", "episode_id"),)
