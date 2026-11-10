from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import tmdb
from app.api_docs import UNAUTHORIZED, VALIDATION, error
from app.config import Settings, get_settings
from app.database import get_db_session
from app.deps import get_current_user
from app.exceptions import ApiError
from app.models import LibraryEntry, MediaTitle, User

router = APIRouter(prefix="/api/me/titles", tags=["library"])

LIBRARY_STATUSES = ("planned", "in_progress", "completed", "on_hold", "dropped")
LibraryStatus = Literal["planned", "in_progress", "completed", "on_hold", "dropped"]
MediaType = Literal["movie", "series", "game"]
Provider = Literal["tmdb", "rawg"]

STATUS_HELP = (
    "planned — у планах, in_progress — дивлюсь / граю, completed — завершено, "
    "on_hold — на паузі, dropped — закинуто."
)


class StatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: LibraryStatus = Field(description=f"Статус: {STATUS_HELP}", examples=["planned"])


REVIEW_MAX_LENGTH = 2000


class EntryPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rating: int | None = Field(
        default=None, ge=1, le=10, description="Оцінка 1–10; null прибирає оцінку.", examples=[8]
    )
    season: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Сезон (від 1); передається разом з episode. "
            "null разом з episode: null скидає прогрес."
        ),
        examples=[2],
    )
    episode: int | None = Field(
        default=None, ge=1, description="Епізод (від 1); передається разом з season.", examples=[5]
    )
    review: str | None = Field(
        default=None,
        max_length=REVIEW_MAX_LENGTH,
        description=(
            f"Відгук до {REVIEW_MAX_LENGTH} символів, пробіли по краях обрізаються; "
            "null видаляє відгук. Порожній рядок — 422."
        ),
        examples=["Чудовий фільм"],
    )

    @model_validator(mode="after")
    def _at_least_one_field(self) -> "EntryPatch":
        provided = self.model_fields_set
        if not provided:
            raise ValueError("Передайте rating, review або season/episode")
        if ("season" in provided) != ("episode" in provided):
            raise ValueError("season і episode передаються разом")
        if "review" in provided and self.review is not None:
            trimmed = self.review.strip()
            if not trimmed:
                raise ValueError("Відгук не може бути порожнім")
            self.review = trimmed
        return self


class LibraryTitleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Id тайтлу в MediaTrack (той самий, що в URL).")
    provider: Provider = Field(description="Джерело: tmdb або rawg (Steam).", examples=["tmdb"])
    media_type: MediaType = Field(description="Тип тайтлу.", examples=["series"])
    external_id: str = Field(description="Id у джерелі.", examples=["1396"])
    title: str = Field(description="Назва.", examples=["Пуститися берега"])
    poster_url: str | None = Field(
        default=None,
        description="URL постера.",
        examples=["https://image.tmdb.org/t/p/w342/ggFHVNu6YYI5L9pCfOacjizRGt.jpg"],
    )
    year: int | None = Field(default=None, description="Рік виходу.", examples=[2008])
    status: LibraryStatus = Field(description=f"Статус: {STATUS_HELP}", examples=["in_progress"])
    rating: int | None = Field(default=None, description="Оцінка 1–10 або null.", examples=[8])
    current_season: int | None = Field(
        default=None, description="Сезон, на якому зупинились (лише серіали).", examples=[2]
    )
    current_episode: int | None = Field(
        default=None, description="Епізод, на якому зупинились (лише серіали).", examples=[5]
    )
    review: str | None = Field(
        default=None, description="Відгук або null.", examples=["Чудовий серіал"]
    )
    review_updated_at: datetime | None = Field(
        default=None,
        description="Коли відгук востаннє змінювали (UTC); null, якщо відгуку немає.",
    )


class EntryResponse(BaseModel):
    entry: LibraryTitleOut


class ListResponse(BaseModel):
    items: list[LibraryTitleOut] = Field(
        description="Записи, від нещодавно змінених до старіших."
    )


TitleIdParam = Annotated[
    UUID,
    Path(
        description=(
            "Id тайтлу в MediaTrack: поле `title.id` з `GET /api/titles/...` (не external_id)."
        )
    ),
]

_TITLE_NOT_FOUND = error("Тайтлу з таким id немає в БД.", "Тайтл не знайдено")
_ENTRY_NOT_FOUND = error("Тайтлу немає у списках користувача.", "Тайтлу немає у ваших списках")

PATCH_EXAMPLES = {
    "rating": {"summary": "Поставити оцінку", "value": {"rating": 8}},
    "review": {"summary": "Написати або змінити відгук", "value": {"review": "Чудовий фільм"}},
    "progress": {"summary": "Зберегти прогрес серіалу", "value": {"season": 2, "episode": 5}},
    "clear_rating": {"summary": "Прибрати оцінку", "value": {"rating": None}},
    "clear_review": {"summary": "Видалити відгук", "value": {"review": None}},
    "clear_progress": {
        "summary": "Скинути прогрес",
        "value": {"season": None, "episode": None},
    },
}


def _to_out(entry: LibraryEntry, title: MediaTitle) -> LibraryTitleOut:
    year = title.release_date.year if title.release_date else None
    return LibraryTitleOut(
        id=title.id,
        provider=title.provider,
        media_type=title.media_type,
        external_id=title.external_id,
        title=title.title,
        poster_url=title.poster_url,
        year=year,
        status=entry.status,  # type: ignore[arg-type]
        rating=entry.rating,
        current_season=entry.current_season,
        current_episode=entry.current_episode,
        review=entry.review_text,
        review_updated_at=entry.review_updated_at,
    )


def _load_entry(
    db: Session, user_id: UUID, title_id: UUID
) -> tuple[LibraryEntry, MediaTitle] | None:
    row = db.execute(
        select(LibraryEntry, MediaTitle)
        .join(MediaTitle, MediaTitle.id == LibraryEntry.title_id)
        .where(LibraryEntry.user_id == user_id, LibraryEntry.title_id == title_id)
    ).one_or_none()
    if row is None:
        return None
    entry, title = row
    return entry, title


@router.get(
    "",
    response_model=ListResponse,
    summary="Мої списки",
    description="Усі тайтли користувача з його статусами, оцінками, відгуками й прогресом.",
    responses={**UNAUTHORIZED, **VALIDATION},
)
def list_entries(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
    _settings: Annotated[Settings, Depends(get_settings)],
    status_filter: Annotated[
        LibraryStatus | None, Query(alias="status", description="Фільтр за статусом.")
    ] = None,
    type_filter: Annotated[
        MediaType | None, Query(alias="type", description="Фільтр за типом тайтлу.")
    ] = None,
) -> ListResponse:
    query = (
        select(LibraryEntry, MediaTitle)
        .join(MediaTitle, MediaTitle.id == LibraryEntry.title_id)
        .where(LibraryEntry.user_id == user.id)
    )
    if status_filter is not None:
        query = query.where(LibraryEntry.status == status_filter)
    if type_filter is not None:
        query = query.where(MediaTitle.media_type == type_filter)
    query = query.order_by(LibraryEntry.updated_at.desc())
    rows = db.execute(query).all()
    return ListResponse(items=[_to_out(entry, title) for entry, title in rows])


@router.get(
    "/{title_id}",
    response_model=EntryResponse,
    summary="Мій запис про тайтл",
    description="Статус, оцінка, відгук і прогрес користувача для одного тайтлу.",
    responses={**UNAUTHORIZED, 404: _ENTRY_NOT_FOUND, **VALIDATION},
)
def get_entry(
    title_id: TitleIdParam,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> EntryResponse:
    row = _load_entry(db, user.id, title_id)
    if row is None:
        raise ApiError(status_code=404, detail="Тайтлу немає у ваших списках")
    return EntryResponse(entry=_to_out(*row))


@router.put(
    "/{title_id}",
    response_model=EntryResponse,
    summary="Додати в списки або змінити статус",
    description=(
        "Створює запис зі статусом або змінює статус наявного. "
        "Оцінка, відгук і прогрес при цьому не змінюються."
    ),
    responses={**UNAUTHORIZED, 404: _TITLE_NOT_FOUND, **VALIDATION},
)
def put_entry(
    title_id: TitleIdParam,
    payload: StatusUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> EntryResponse:
    title = db.get(MediaTitle, title_id)
    if title is None:
        raise ApiError(status_code=404, detail="Тайтл не знайдено")

    entry = db.execute(
        select(LibraryEntry).where(
            LibraryEntry.user_id == user.id,
            LibraryEntry.title_id == title_id,
        )
    ).scalar_one_or_none()

    if entry is None:
        entry = LibraryEntry(user_id=user.id, title_id=title_id, status=payload.status)
        db.add(entry)
    else:
        entry.status = payload.status

    db.commit()
    db.refresh(entry)
    return EntryResponse(entry=_to_out(entry, title))


async def _validate_progress(
    title: MediaTitle, season: int, episode: int, settings: Settings
) -> None:
    if title.media_type != "series":
        raise ApiError(
            status_code=400,
            detail="Прогрес серій доступний лише для серіалів",
            fields={"season": "Прогрес доступний лише для серіалів"},
        )
    try:
        seasons = await tmdb.fetch_tv_seasons(title.external_id, settings)
    except tmdb.TMDBError as exc:
        raise ApiError(status_code=503, detail="Не вдалося звіритися з TMDB") from exc

    match = next((s for s in seasons if s.season_number == season), None)
    if match is None:
        raise ApiError(
            status_code=400,
            detail="Такого сезону немає",
            fields={"season": "Такого сезону немає"},
        )
    if episode > match.episode_count:
        raise ApiError(
            status_code=400,
            detail="Такого епізоду немає",
            fields={"episode": f"У сезоні лише {match.episode_count} епізодів"},
        )


@router.patch(
    "/{title_id}",
    response_model=EntryResponse,
    summary="Оцінка, відгук або прогрес",
    description=(
        "Змінює лише передані поля; `null` прибирає значення. Правила:\n\n"
        "- треба передати хоча б одне поле; `season` і `episode` — тільки разом;\n"
        "- якщо тайтлу ще немає у списках, оцінка або відгук додають його зі статусом "
        "`completed`, прогрес — зі статусом `in_progress`; лише очищення — 404;\n"
        "- для наявного запису статус не змінюється;\n"
        "- прогрес доступний лише для серіалів і звіряється з TMDB: неіснуючий сезон чи "
        "епізод — 400 з поясненням у `fields`.\n\n"
        "Порушення правил першого пункту і порожній відгук дають 422 із загальним "
        "повідомленням без `fields`."
    ),
    responses={
        400: error(
            "Прогрес для не-серіалу, неіснуючий сезон або епізод.",
            "Такого епізоду немає",
            {"episode": "У сезоні лише 8 епізодів"},
        ),
        **UNAUTHORIZED,
        404: error(
            "Тайтлу немає в БД, або запису немає і запит лише очищує значення.",
            "Тайтл не знайдено",
        ),
        **VALIDATION,
        503: error("TMDB не відповів під час перевірки прогресу.", "Не вдалося звіритися з TMDB"),
    },
)
async def patch_entry(
    title_id: TitleIdParam,
    payload: Annotated[EntryPatch, Body(openapi_examples=PATCH_EXAMPLES)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> EntryResponse:
    title = db.get(MediaTitle, title_id)
    if title is None:
        raise ApiError(status_code=404, detail="Тайтл не знайдено")

    provided = payload.model_fields_set
    sets_rating = "rating" in provided
    sets_progress = "season" in provided and "episode" in provided
    sets_review = "review" in provided

    if sets_progress and payload.season is not None and payload.episode is not None:
        await _validate_progress(title, payload.season, payload.episode, settings)

    entry = db.execute(
        select(LibraryEntry).where(
            LibraryEntry.user_id == user.id,
            LibraryEntry.title_id == title_id,
        )
    ).scalar_one_or_none()

    def _apply_review(target: LibraryEntry) -> None:
        if payload.review is None:
            target.review_text = None
            target.review_updated_at = None
        else:
            target.review_text = payload.review
            target.review_updated_at = datetime.now(timezone.utc)

    if entry is None:
        only_clearing = (
            (not sets_rating or payload.rating is None)
            and (not sets_progress or payload.season is None)
            and (not sets_review or payload.review is None)
        )
        if only_clearing:
            raise ApiError(status_code=404, detail="Тайтлу немає у ваших списках")
        has_rating = sets_rating and payload.rating is not None
        has_review = sets_review and payload.review is not None
        initial_status = "completed" if has_rating or has_review else "in_progress"
        entry = LibraryEntry(
            user_id=user.id,
            title_id=title_id,
            status=initial_status,
        )
        if sets_rating:
            entry.rating = payload.rating
        if sets_progress:
            entry.current_season = payload.season
            entry.current_episode = payload.episode
        if sets_review:
            _apply_review(entry)
        db.add(entry)
    else:
        if sets_rating:
            entry.rating = payload.rating
        if sets_progress:
            entry.current_season = payload.season
            entry.current_episode = payload.episode
        if sets_review:
            _apply_review(entry)

    db.commit()
    db.refresh(entry)
    return EntryResponse(entry=_to_out(entry, title))


@router.delete(
    "/{title_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Прибрати зі списків",
    description=(
        "Видаляє запис разом з оцінкою, відгуком і прогресом. Сам тайтл лишається в БД. "
        "Повторне видалення теж повертає 204."
    ),
    responses={
        204: {"description": "Запис видалено (або його й не було)."},
        **UNAUTHORIZED,
        **VALIDATION,
    },
)
def delete_entry(
    title_id: TitleIdParam,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> Response:
    db.execute(
        delete(LibraryEntry).where(
            LibraryEntry.user_id == user.id,
            LibraryEntry.title_id == title_id,
        )
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
