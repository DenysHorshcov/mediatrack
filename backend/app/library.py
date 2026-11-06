from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db_session
from app.deps import get_current_user
from app.exceptions import ApiError
from app.models import LibraryEntry, MediaTitle, User

router = APIRouter(prefix="/api/me/titles", tags=["library"])

LIBRARY_STATUSES = ("planned", "in_progress", "completed", "on_hold", "dropped")
LibraryStatus = Literal["planned", "in_progress", "completed", "on_hold", "dropped"]
MediaType = Literal["movie", "series", "game"]


class StatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: LibraryStatus


class EntryPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rating: int | None = Field(..., ge=1, le=10)


class LibraryTitleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: str
    media_type: str
    external_id: str
    title: str
    poster_url: str | None = None
    year: int | None = None
    status: LibraryStatus
    rating: int | None = None


class EntryResponse(BaseModel):
    entry: LibraryTitleOut


class ListResponse(BaseModel):
    items: list[LibraryTitleOut]


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


@router.get("", response_model=ListResponse)
def list_entries(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
    _settings: Annotated[Settings, Depends(get_settings)],
    status_filter: Annotated[LibraryStatus | None, Query(alias="status")] = None,
    type_filter: Annotated[MediaType | None, Query(alias="type")] = None,
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


@router.get("/{title_id}", response_model=EntryResponse)
def get_entry(
    title_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> EntryResponse:
    row = _load_entry(db, user.id, title_id)
    if row is None:
        raise ApiError(status_code=404, detail="Тайтлу немає у ваших списках")
    return EntryResponse(entry=_to_out(*row))


@router.put("/{title_id}", response_model=EntryResponse)
def put_entry(
    title_id: UUID,
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


@router.patch("/{title_id}", response_model=EntryResponse)
def patch_entry(
    title_id: UUID,
    payload: EntryPatch,
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
        if payload.rating is None:
            raise ApiError(status_code=404, detail="Тайтлу немає у ваших списках")
        entry = LibraryEntry(
            user_id=user.id,
            title_id=title_id,
            status="completed",
            rating=payload.rating,
        )
        db.add(entry)
    else:
        entry.rating = payload.rating

    db.commit()
    db.refresh(entry)
    return EntryResponse(entry=_to_out(entry, title))


@router.delete("/{title_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    title_id: UUID,
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
