"""add current_season and current_episode to library_entries

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "library_entries",
        sa.Column("current_season", sa.Integer(), nullable=True),
    )
    op.add_column(
        "library_entries",
        sa.Column("current_episode", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_library_entries_progress_range",
        "library_entries",
        "(current_season IS NULL AND current_episode IS NULL) OR "
        "(current_season >= 1 AND current_episode >= 1)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_library_entries_progress_range", "library_entries", type_="check"
    )
    op.drop_column("library_entries", "current_episode")
    op.drop_column("library_entries", "current_season")
