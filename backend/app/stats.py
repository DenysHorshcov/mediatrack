from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.deps import get_current_user
from app.models import LibraryEntry, MediaTitle, User

router = APIRouter(prefix="/api/me/stats", tags=["stats"])


MEDIA_TYPES = ("movie", "series", "game")
STATUSES = ("planned", "in_progress", "completed", "on_hold", "dropped")


class ByMediaType(BaseModel):
    movie: int = 0
    series: int = 0
    game: int = 0


class ByStatus(BaseModel):
    planned: int = 0
    in_progress: int = 0
    completed: int = 0
    on_hold: int = 0
    dropped: int = 0


class StatsResponse(BaseModel):
    total: int
    by_type: ByMediaType
    by_status: ByStatus
    average_rating: float | None
    completed_this_year: int


@router.get("", response_model=StatsResponse)
def get_stats(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> StatsResponse:
    year_now = datetime.now(timezone.utc).year

    # Counts by media type.
    type_rows = db.execute(
        select(MediaTitle.media_type, func.count(LibraryEntry.id))
        .join(MediaTitle, MediaTitle.id == LibraryEntry.title_id)
        .where(LibraryEntry.user_id == user.id)
        .group_by(MediaTitle.media_type)
    ).all()
    by_type = ByMediaType(**{t: c for t, c in type_rows if t in MEDIA_TYPES})

    # Counts by status.
    status_rows = db.execute(
        select(LibraryEntry.status, func.count(LibraryEntry.id))
        .where(LibraryEntry.user_id == user.id)
        .group_by(LibraryEntry.status)
    ).all()
    by_status = ByStatus(**{s: c for s, c in status_rows if s in STATUSES})

    # Average rating across all rated entries.
    avg_raw = db.execute(
        select(func.avg(LibraryEntry.rating)).where(LibraryEntry.user_id == user.id)
    ).scalar_one_or_none()
    average_rating = round(float(avg_raw), 1) if avg_raw is not None else None

    # Count completed titles whose entry was updated this year
    # (updated_at bumps on status change into 'completed').
    completed_this_year = db.execute(
        select(func.count(LibraryEntry.id)).where(
            LibraryEntry.user_id == user.id,
            LibraryEntry.status == "completed",
            func.extract("year", LibraryEntry.updated_at) == year_now,
        )
    ).scalar_one()

    total = sum((by_type.movie, by_type.series, by_type.game))

    return StatsResponse(
        total=total,
        by_type=by_type,
        by_status=by_status,
        average_rating=average_rating,
        completed_this_year=completed_this_year,
    )
