import asyncio
import logging
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app import rawg, tmdb
from app.api_docs import UNAUTHORIZED, VALIDATION, error
from app.config import Settings, get_settings
from app.deps import get_current_user
from app.exceptions import ApiError
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchType(str, Enum):
    all = "all"
    movie = "movie"
    series = "series"
    game = "game"


class SearchResponse(BaseModel):
    results: list[tmdb.SearchItem] = Field(
        description="Результати: спершу фільми й серіали з TMDB, потім ігри зі Steam."
    )


async def _safe_tmdb(q: str, settings: Settings) -> tuple[list[tmdb.SearchItem], Exception | None]:
    try:
        return await tmdb.search_titles(q, settings), None
    except tmdb.TMDBError as exc:
        logger.warning("TMDB search failed: %s", exc)
        return [], exc


async def _safe_rawg(q: str, settings: Settings) -> tuple[list[tmdb.SearchItem], Exception | None]:
    try:
        return await rawg.search_games(q, settings), None
    except rawg.RAWGError as exc:
        logger.warning("Games search failed: %s", exc)
        return [], exc


@router.get(
    "",
    response_model=SearchResponse,
    summary="Пошук тайтлів",
    description=(
        "Шукає фільми й серіали в TMDB (українською) та ігри в Steam (англійською). "
        "Персони з TMDB, саундтреки й DLC зі Steam відкидаються. Якщо одне джерело "
        "недоступне, повертаються результати іншого; 503 — лише коли не відповіло жодне "
        "і результатів немає."
    ),
    responses={
        **UNAUTHORIZED,
        **VALIDATION,
        503: error(
            "Жодне з потрібних джерел (TMDB, Steam) не відповіло.",
            "Пошук тимчасово недоступний. Спробуйте пізніше.",
        ),
    },
)
async def search(
    q: Annotated[
        str,
        Query(min_length=1, max_length=200, description="Пошуковий запит.", examples=["Матриця"]),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[User, Depends(get_current_user)],
    type: Annotated[
        SearchType,
        Query(description="Що шукати: all — усе, movie / series — лише TMDB, game — лише Steam."),
    ] = SearchType.all,
) -> SearchResponse:
    want_titles = type in (SearchType.all, SearchType.movie, SearchType.series)
    want_games = type in (SearchType.all, SearchType.game)

    tmdb_task = _safe_tmdb(q, settings) if want_titles else None
    rawg_task = _safe_rawg(q, settings) if want_games else None
    tasks = [t for t in (tmdb_task, rawg_task) if t is not None]
    outcomes = await asyncio.gather(*tasks)

    results: list[tmdb.SearchItem] = []
    errors: list[Exception] = []
    for items, error in outcomes:
        results.extend(items)
        if error is not None:
            errors.append(error)

    if type == SearchType.movie:
        results = [r for r in results if r.type == "movie"]
    elif type == SearchType.series:
        results = [r for r in results if r.type == "series"]

    if not results and errors:
        raise ApiError(
            status_code=503,
            detail="Пошук тимчасово недоступний. Спробуйте пізніше.",
        )

    return SearchResponse(results=results)
