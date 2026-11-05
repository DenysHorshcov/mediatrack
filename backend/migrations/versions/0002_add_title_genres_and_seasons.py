"""add genres and seasons_count to media_titles

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "media_titles",
        sa.Column("genres", sa.Text(), nullable=True),
    )
    op.add_column(
        "media_titles",
        sa.Column("seasons_count", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_media_titles_seasons_count_range",
        "media_titles",
        "seasons_count IS NULL OR (seasons_count >= 0 AND media_type = 'series')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_media_titles_seasons_count_range", "media_titles", type_="check"
    )
    op.drop_column("media_titles", "seasons_count")
    op.drop_column("media_titles", "genres")
