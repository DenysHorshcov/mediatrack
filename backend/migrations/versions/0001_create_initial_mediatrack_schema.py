"""create initial MediaTrack schema

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media_titles",
        sa.Column("provider", sa.String(length=10), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("media_type", sa.String(length=10), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("original_title", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("description_language", sa.String(length=10), nullable=True),
        sa.Column("poster_url", sa.Text(), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.CheckConstraint(
            "(description IS NULL AND description_language IS NULL) OR (description IS NOT NULL AND description_language IS NOT NULL AND description_language IN ('uk', 'en') AND length(btrim(description)) > 0)",
            name=op.f("ck_media_titles_description_language"),
        ),
        sa.CheckConstraint(
            "(provider = 'tmdb' AND media_type IN ('movie', 'series')) OR (provider = 'rawg' AND media_type = 'game')",
            name=op.f("ck_media_titles_provider_media_type"),
        ),
        sa.CheckConstraint(
            "external_id = btrim(external_id) AND length(external_id) > 0",
            name=op.f("ck_media_titles_external_id_trimmed"),
        ),
        sa.CheckConstraint(
            "title = btrim(title) AND length(title) > 0",
            name=op.f("ck_media_titles_title_trimmed"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_titles")),
        sa.UniqueConstraint(
            "provider",
            "media_type",
            "external_id",
            name="uq_media_titles_external_identity",
        ),
    )
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "email = btrim(email) AND length(email) > 0",
            name=op.f("ck_users_email_trimmed"),
        ),
        sa.CheckConstraint(
            "length(btrim(password_hash)) > 0",
            name=op.f("ck_users_password_hash_not_blank"),
        ),
        sa.CheckConstraint(
            "username = btrim(username) AND length(username) > 0",
            name=op.f("ck_users_username_trimmed"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(
        "uq_users_email_lower",
        "users",
        [sa.literal_column("lower(email)")],
        unique=True,
    )
    op.create_index(
        "uq_users_username_lower",
        "users",
        [sa.literal_column("lower(username)")],
        unique=True,
    )
    op.create_table(
        "library_entries",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'planned'"),
            nullable=False,
        ),
        sa.Column("rating", sa.SmallInteger(), nullable=True),
        sa.Column("review_text", sa.Text(), nullable=True),
        sa.Column("review_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('planned', 'in_progress', 'completed', 'on_hold', 'dropped')",
            name=op.f("ck_library_entries_status_values"),
        ),
        sa.CheckConstraint(
            "rating IS NULL OR rating BETWEEN 1 AND 10",
            name=op.f("ck_library_entries_rating_range"),
        ),
        sa.ForeignKeyConstraint(
            ["title_id"],
            ["media_titles.id"],
            name=op.f("fk_library_entries_title_id_media_titles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_library_entries_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_library_entries")),
        sa.UniqueConstraint(
            "user_id", "title_id", name=op.f("uq_library_entries_user_id_title_id")
        ),
    )
    op.create_index(
        "ix_library_entries_title_id", "library_entries", ["title_id"], unique=False
    )
    op.create_table(
        "seasons",
        sa.Column("title_id", sa.Uuid(), nullable=False),
        sa.Column("season_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("air_date", sa.Date(), nullable=True),
        sa.Column("episodes_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.CheckConstraint(
            "season_number >= 0", name=op.f("ck_seasons_season_number_range")
        ),
        sa.ForeignKeyConstraint(
            ["title_id"],
            ["media_titles.id"],
            name=op.f("fk_seasons_title_id_media_titles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_seasons")),
        sa.UniqueConstraint(
            "title_id", "season_number", name=op.f("uq_seasons_title_id_season_number")
        ),
    )
    op.create_table(
        "episodes",
        sa.Column("season_id", sa.Uuid(), nullable=False),
        sa.Column("episode_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("air_date", sa.Date(), nullable=True),
        sa.Column("runtime_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.CheckConstraint(
            "episode_number >= 1", name=op.f("ck_episodes_episode_number_range")
        ),
        sa.CheckConstraint(
            "runtime_minutes IS NULL OR runtime_minutes > 0",
            name=op.f("ck_episodes_runtime_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["season_id"],
            ["seasons.id"],
            name=op.f("fk_episodes_season_id_seasons"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_episodes")),
        sa.UniqueConstraint(
            "season_id",
            "episode_number",
            name=op.f("uq_episodes_season_id_episode_number"),
        ),
    )
    op.create_table(
        "watched_episodes",
        sa.Column("library_entry_id", sa.Uuid(), nullable=False),
        sa.Column("episode_id", sa.Uuid(), nullable=False),
        sa.Column(
            "watched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["episode_id"],
            ["episodes.id"],
            name=op.f("fk_watched_episodes_episode_id_episodes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["library_entry_id"],
            ["library_entries.id"],
            name=op.f("fk_watched_episodes_library_entry_id_library_entries"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "library_entry_id", "episode_id", name=op.f("pk_watched_episodes")
        ),
    )
    op.create_index(
        "ix_watched_episodes_episode_id",
        "watched_episodes",
        ["episode_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_watched_episodes_episode_id", table_name="watched_episodes")
    op.drop_table("watched_episodes")
    op.drop_table("episodes")
    op.drop_table("seasons")
    op.drop_index("ix_library_entries_title_id", table_name="library_entries")
    op.drop_table("library_entries")
    op.drop_index("uq_users_username_lower", table_name="users")
    op.drop_index("uq_users_email_lower", table_name="users")
    op.drop_table("users")
    op.drop_table("media_titles")
