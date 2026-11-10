"""Thin TMDB client. Only /search/multi used for now."""

from typing import Literal

import httpx
from pydantic import BaseModel, Field

from app.config import Settings


class SearchItem(BaseModel):
    id: str = Field(
        description=(
            "Id у джерелі: TMDB id для фільмів і серіалів, Steam appid для ігор. "
            "Це `external_id` для `GET /api/titles/{provider}/{media_type}/{external_id}`."
        ),
        examples=["603"],
    )
    type: Literal["movie", "series", "game"] = Field(
        description="Тип: movie і series — з TMDB (provider tmdb), game — зі Steam (provider rawg).",
        examples=["movie"],
    )
    title: str = Field(description="Назва (для TMDB — українською, якщо є).", examples=["Матриця"])
    year: int | None = Field(default=None, description="Рік виходу; null, якщо невідомий.", examples=[1999])
    poster: str | None = Field(
        default=None,
        description="URL постера; null, якщо постера немає.",
        examples=["https://image.tmdb.org/t/p/w342/matrix.jpg"],
    )


class TMDBError(Exception):
    """Raised when TMDB cannot answer. Mapped to 503 at the router."""


def _year(date_str: str | None) -> int | None:
    if not date_str:
        return None
    prefix = date_str[:4]
    return int(prefix) if prefix.isdigit() else None


def _poster(path: str | None, base: str) -> str | None:
    return f"{base}{path}" if path else None


def _map_item(item: dict, image_base: str) -> SearchItem | None:
    media_type = item.get("media_type")
    item_id = item.get("id")
    if not item_id:
        return None
    if media_type == "movie":
        title = item.get("title") or item.get("original_title")
        if not title:
            return None
        return SearchItem(
            id=str(item_id),
            type="movie",
            title=title,
            year=_year(item.get("release_date")),
            poster=_poster(item.get("poster_path"), image_base),
        )
    if media_type == "tv":
        title = item.get("name") or item.get("original_name")
        if not title:
            return None
        return SearchItem(
            id=str(item_id),
            type="series",
            title=title,
            year=_year(item.get("first_air_date")),
            poster=_poster(item.get("poster_path"), image_base),
        )
    # media_type == "person" and anything else — ignore
    return None


async def search_titles(query: str, settings: Settings) -> list[SearchItem]:
    query = query.strip()
    if not query:
        return []
    if settings.tmdb_api_key is None:
        raise TMDBError("TMDB_API_KEY is not configured")

    try:
        async with httpx.AsyncClient(timeout=settings.tmdb_timeout_seconds) as client:
            response = await client.get(
                f"{settings.tmdb_base_url}/search/multi",
                params={
                    "api_key": settings.tmdb_api_key.get_secret_value(),
                    "query": query,
                    "language": settings.tmdb_language,
                    "include_adult": "false",
                },
            )
    except httpx.HTTPError as exc:
        raise TMDBError("TMDB request failed") from exc

    if response.status_code != 200:
        raise TMDBError(f"TMDB status {response.status_code}")

    payload = response.json()
    items: list[SearchItem] = []
    for raw in payload.get("results", []):
        mapped = _map_item(raw, settings.tmdb_image_base_url)
        if mapped is not None:
            items.append(mapped)
    return items


class TitleDetails(BaseModel):
    title: str
    original_title: str | None = None
    description: str | None = None
    description_language: str | None = None  # "uk" | "en"
    poster_url: str | None = None
    release_date: str | None = None  # ISO date yyyy-mm-dd
    genres: list[str] = []
    seasons_count: int | None = None


def _tmdb_detail_path(media_type: str, external_id: str) -> str:
    if media_type == "movie":
        return f"/movie/{external_id}"
    if media_type == "series":
        return f"/tv/{external_id}"
    raise TMDBError(f"Unsupported media_type: {media_type}")


def _map_details(
    payload: dict, media_type: str, language: str, image_base: str
) -> TitleDetails:
    title_key = "title" if media_type == "movie" else "name"
    original_key = "original_title" if media_type == "movie" else "original_name"
    date_key = "release_date" if media_type == "movie" else "first_air_date"

    poster_path = payload.get("poster_path")
    description = (payload.get("overview") or "").strip() or None
    description_language = language if description else None

    return TitleDetails(
        title=payload.get(title_key) or payload.get(original_key) or "",
        original_title=payload.get(original_key),
        description=description,
        description_language=description_language,
        poster_url=f"{image_base}{poster_path}" if poster_path else None,
        release_date=payload.get(date_key) or None,
        genres=[g.get("name", "") for g in payload.get("genres", []) if g.get("name")],
        seasons_count=(
            payload.get("number_of_seasons") if media_type == "series" else None
        ),
    )


class SeasonSummary(BaseModel):
    season_number: int
    name: str | None = None
    air_date: str | None = None
    episode_count: int


async def fetch_tv_seasons(
    external_id: str, settings: Settings
) -> list[SeasonSummary]:
    if settings.tmdb_api_key is None:
        raise TMDBError("TMDB_API_KEY is not configured")
    url = f"{settings.tmdb_base_url}/tv/{external_id}"
    try:
        async with httpx.AsyncClient(timeout=settings.tmdb_timeout_seconds) as client:
            response = await client.get(
                url,
                params={
                    "api_key": settings.tmdb_api_key.get_secret_value(),
                    "language": "uk-UA",
                },
            )
    except httpx.HTTPError as exc:
        raise TMDBError("TMDB request failed") from exc

    if response.status_code == 404:
        raise TMDBError("Series not found")
    if response.status_code != 200:
        raise TMDBError(f"TMDB status {response.status_code}")

    seasons: list[SeasonSummary] = []
    for raw in response.json().get("seasons", []):
        number = raw.get("season_number")
        episodes = raw.get("episode_count")
        if number is None or episodes is None:
            continue
        if number < 1 or episodes < 1:
            continue
        seasons.append(
            SeasonSummary(
                season_number=number,
                name=raw.get("name") or None,
                air_date=raw.get("air_date") or None,
                episode_count=episodes,
            )
        )
    seasons.sort(key=lambda s: s.season_number)
    return seasons


async def fetch_title_details(
    media_type: str, external_id: str, settings: Settings
) -> TitleDetails:
    if settings.tmdb_api_key is None:
        raise TMDBError("TMDB_API_KEY is not configured")

    path = _tmdb_detail_path(media_type, external_id)
    url = f"{settings.tmdb_base_url}{path}"
    api_key = settings.tmdb_api_key.get_secret_value()

    try:
        async with httpx.AsyncClient(timeout=settings.tmdb_timeout_seconds) as client:
            uk = await client.get(url, params={"api_key": api_key, "language": "uk-UA"})
            if uk.status_code == 404:
                raise TMDBError("Title not found")
            if uk.status_code != 200:
                raise TMDBError(f"TMDB status {uk.status_code}")
            details = _map_details(
                uk.json(), media_type, "uk", settings.tmdb_image_base_url
            )
            if details.description is None:
                en = await client.get(
                    url, params={"api_key": api_key, "language": "en-US"}
                )
                if en.status_code == 200:
                    en_details = _map_details(
                        en.json(), media_type, "en", settings.tmdb_image_base_url
                    )
                    if en_details.description:
                        details.description = en_details.description
                        details.description_language = "en"
            return details
    except httpx.HTTPError as exc:
        raise TMDBError("TMDB request failed") from exc
