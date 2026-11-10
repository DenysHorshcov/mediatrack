from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import rawg, tmdb
from app.api_docs import UNAUTHORIZED, VALIDATION, error
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

    id: UUID = Field(
        description="Id тайтлу в MediaTrack. Саме його передають у `/api/me/titles/{title_id}`."
    )
    provider: Provider = Field(
        description="Джерело: tmdb — фільми й серіали, rawg — ігри зі Steam.", examples=["tmdb"]
    )
    media_type: MediaType = Field(description="Тип тайтлу.", examples=["movie"])
    external_id: str = Field(description="Id у джерелі (TMDB id або Steam appid).", examples=["603"])
    title: str = Field(description="Назва.", examples=["Матриця"])
    original_title: str | None = Field(
        default=None, description="Оригінальна назва (лише TMDB).", examples=["The Matrix"]
    )
    description: str | None = Field(default=None, description="Опис; null, якщо його немає ніде.")
    description_language: Literal["uk", "en"] | None = Field(
        default=None,
        description="Мова опису: uk або en (якщо українського немає); null, коли опису немає.",
        examples=["uk"],
    )
    poster_url: str | None = Field(
        default=None,
        description="URL постера.",
        examples=["https://image.tmdb.org/t/p/w342/matrix.jpg"],
    )
    year: int | None = Field(default=None, description="Рік виходу.", examples=[1999])
    genres: list[str] = Field(default=[], description="Жанри.", examples=[["Фантастика", "Бойовик"]])
    seasons_count: int | None = Field(
        default=None, description="Кількість сезонів (лише для серіалів).", examples=[5]
    )


class TitleResponse(BaseModel):
    title: TitleOut


class SeasonOut(BaseModel):
    season_number: int = Field(description="Номер сезону (від 1; спецвипуски не повертаються).", examples=[1])
    name: str | None = Field(default=None, description="Назва сезону.", examples=["Сезон 1"])
    air_date: str | None = Field(
        default=None, description="Дата виходу у форматі YYYY-MM-DD.", examples=["2008-01-20"]
    )
    episode_count: int = Field(description="Кількість епізодів.", examples=[7])


class SeasonsResponse(BaseModel):
    seasons: list[SeasonOut] = Field(description="Сезони за зростанням номера.")


_PROVIDER_PARAM = Path(
    min_length=1,
    max_length=10,
    description="Джерело: tmdb (фільми, серіали) або rawg (ігри зі Steam).",
    examples=["tmdb"],
    json_schema_extra={"enum": ["tmdb", "rawg"]},
)
_MEDIA_TYPE_PARAM = Path(
    min_length=1,
    max_length=10,
    description="Тип: movie або series для tmdb, game для rawg. Інша комбінація — 404.",
    examples=["movie"],
    json_schema_extra={"enum": ["movie", "series", "game"]},
)
_EXTERNAL_ID_PARAM = Path(
    min_length=1,
    max_length=64,
    description="Id у джерелі: поле `id` з результатів пошуку.",
    examples=["603"],
)
_NOT_FOUND = {
    404: error(
        "Невідома комбінація provider/media_type або джерело не знає такого id.",
        "Такого тайтлу немає",
    )
}


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
    summary="Картка тайтлу",
    description=(
        "Повертає картку тайтлу. Перший запит тягне дані з TMDB або Steam і зберігає їх у БД; "
        "наступні беруться з БД без запиту до джерела. Якщо українського опису немає, "
        "береться англійський (`description_language = en`)."
    ),
    responses={**UNAUTHORIZED, **_NOT_FOUND, **VALIDATION},
)
async def get_title(
    provider: Annotated[str, _PROVIDER_PARAM],
    media_type: Annotated[str, _MEDIA_TYPE_PARAM],
    external_id: Annotated[str, _EXTERNAL_ID_PARAM],
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
    summary="Сезони серіалу",
    description=(
        "Список сезонів з кількістю епізодів — для вибору прогресу. "
        "Дані завжди беруться з TMDB, у БД не зберігаються. Лише для `tmdb/series`."
    ),
    responses={
        **UNAUTHORIZED,
        404: error(
            "Не серіал TMDB або TMDB не знає такого серіалу.",
            "Сезони доступні лише для серіалів TMDB",
        ),
        **VALIDATION,
    },
)
async def get_seasons(
    provider: Annotated[str, _PROVIDER_PARAM],
    media_type: Annotated[str, _MEDIA_TYPE_PARAM],
    external_id: Annotated[str, _EXTERNAL_ID_PARAM],
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
