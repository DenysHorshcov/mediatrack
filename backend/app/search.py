from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app import tmdb
from app.config import Settings, get_settings
from app.deps import get_current_user
from app.exceptions import ApiError
from app.models import User

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchResponse(BaseModel):
    results: list[tmdb.SearchItem]


@router.get("", response_model=SearchResponse)
async def search(
    q: Annotated[str, Query(min_length=1, max_length=200)],
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[User, Depends(get_current_user)],
) -> SearchResponse:
    try:
        results = await tmdb.search_titles(q, settings)
    except tmdb.TMDBError as exc:
        raise ApiError(
            status_code=503,
            detail="Пошук тимчасово недоступний. Спробуйте пізніше.",
        ) from exc
    return SearchResponse(results=results)
