"""Thin TMDB client. Only /search/multi used for now."""

import httpx
from pydantic import BaseModel

from app.config import Settings


class SearchItem(BaseModel):
    id: str
    type: str
    title: str
    year: int | None = None
    poster: str | None = None


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
