from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import rawg, tmdb
from app.config import Settings, get_settings
from app.database import get_db_session
from app.deps import get_current_user
from app.exceptions import ApiError
from app.models import MediaTitle, User

router = APIRouter(prefix="/api/titles", tags=["titles"])

Provider = Literal["tmdb", "rawg"]
MediaType = Literal["movie", "series", "game"]


class TitleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: str
    media_type: str
    external_id: str
    title: str
    original_title: str | None = None
    description: str | None = None
    description_language: str | None = None
    poster_url: str | None = None
    year: int | None = None
    genres: list[str] = []
    seasons_count: int | None = None


class TitleResponse(BaseModel):
    title: TitleOut


class SeasonOut(BaseModel):
    season_number: int
    name: str | None = None
    air_date: str | None = None
    episode_count: int


class SeasonsResponse(BaseModel):
    seasons: list[SeasonOut]


def _validate_provider_type(provider: str, media_type: str) -> None:
    if provider == "tmdb" and media_type not in ("movie", "series"):
        raise ApiError(404, "Такого тайтлу немає")
    if provider == "rawg" and media_type != "game":
        raise ApiError(404, "Такого тайтлу немає")
    if provider not in ("tmdb", "rawg"):
        raise ApiError(404, "Такого тайтлу немає")


def _to_out(row: MediaTitle) -> TitleOut:
    year = row.release_date.year if isinstance(row.release_date, date) else None
    genres = [g.strip() for g in (row.genres or "").split(",") if g.strip()]
    return TitleOut(
        id=row.id,
        provider=row.provider,
        media_type=row.media_type,
        external_id=row.external_id,
        title=row.title,
        original_title=row.original_title,
        description=row.description,
        description_language=row.description_language,
        poster_url=row.poster_url,
        year=year,
        genres=genres,
        seasons_count=row.seasons_count,
    )


def _parse_release_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


async def _fetch_from_provider(
    provider: str, media_type: str, external_id: str, settings: Settings
) -> tmdb.TitleDetails:
    if provider == "tmdb":
        try:
            return await tmdb.fetch_title_details(media_type, external_id, settings)
        except tmdb.TMDBError as exc:
            raise ApiError(404, "Такого тайтлу немає") from exc
    try:
        return await rawg.fetch_game_details(external_id, settings)
    except rawg.RAWGError as exc:
        raise ApiError(404, "Такого тайтлу немає") from exc


@router.get(
    "/{provider}/{media_type}/{external_id}",
    response_model=TitleResponse,
)
async def get_title(
    provider: Annotated[str, Path(min_length=1, max_length=10)],
    media_type: Annotated[str, Path(min_length=1, max_length=10)],
    external_id: Annotated[str, Path(min_length=1, max_length=64)],
    db: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[User, Depends(get_current_user)],
) -> TitleResponse:
    _validate_provider_type(provider, media_type)

    existing = db.execute(
        select(MediaTitle).where(
            MediaTitle.provider == provider,
            MediaTitle.media_type == media_type,
            MediaTitle.external_id == external_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return TitleResponse(title=_to_out(existing))

    details = await _fetch_from_provider(provider, media_type, external_id, settings)
    if not details.title:
        raise ApiError(404, "Такого тайтлу немає")

    row = MediaTitle(
        provider=provider,
        media_type=media_type,
        external_id=external_id,
        title=details.title,
        original_title=details.original_title,
        description=details.description,
        description_language=details.description_language,
        poster_url=details.poster_url,
        release_date=_parse_release_date(details.release_date),
        genres=", ".join(details.genres) if details.genres else None,
        seasons_count=details.seasons_count,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return TitleResponse(title=_to_out(row))


@router.get(
    "/{provider}/{media_type}/{external_id}/seasons",
    response_model=SeasonsResponse,
)
async def get_seasons(
    provider: Annotated[str, Path(min_length=1, max_length=10)],
    media_type: Annotated[str, Path(min_length=1, max_length=10)],
    external_id: Annotated[str, Path(min_length=1, max_length=64)],
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[User, Depends(get_current_user)],
) -> SeasonsResponse:
    if provider != "tmdb" or media_type != "series":
        raise ApiError(404, "Сезони доступні лише для серіалів TMDB")
    try:
        seasons = await tmdb.fetch_tv_seasons(external_id, settings)
    except tmdb.TMDBError as exc:
        raise ApiError(404, "Серіал не знайдено") from exc
    return SeasonsResponse(
        seasons=[
            SeasonOut(
                season_number=s.season_number,
                name=s.name,
                air_date=s.air_date,
                episode_count=s.episode_count,
            )
            for s in seasons
        ]
    )
