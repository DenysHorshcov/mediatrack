"""Thin RAWG client. Only /games used for now."""

import httpx

from app.config import Settings
from app.tmdb import SearchItem


class RAWGError(Exception):
    """Raised when RAWG cannot answer. Router may swallow it to not break movie search."""


def _year(date_str: str | None) -> int | None:
    if not date_str:
        return None
    prefix = date_str[:4]
    return int(prefix) if prefix.isdigit() else None


def _map_item(item: dict) -> SearchItem | None:
    item_id = item.get("id")
    name = item.get("name")
    if not item_id or not name:
        return None
    return SearchItem(
        id=str(item_id),
        type="game",
        title=name,
        year=_year(item.get("released")),
        poster=item.get("background_image") or None,
    )


async def search_games(query: str, settings: Settings) -> list[SearchItem]:
    query = query.strip()
    if not query:
        return []
    if settings.rawg_api_key is None:
        raise RAWGError("RAWG_API_KEY is not configured")

    try:
        async with httpx.AsyncClient(timeout=settings.rawg_timeout_seconds) as client:
            response = await client.get(
                f"{settings.rawg_base_url}/games",
                params={
                    "key": settings.rawg_api_key.get_secret_value(),
                    "search": query,
                    "page_size": str(settings.rawg_page_size),
                },
            )
    except httpx.HTTPError as exc:
        raise RAWGError("RAWG request failed") from exc

    if response.status_code != 200:
        raise RAWGError(f"RAWG status {response.status_code}")

    payload = response.json()
    items: list[SearchItem] = []
    for raw in payload.get("results", []):
        mapped = _map_item(raw)
        if mapped is not None:
            items.append(mapped)
    return items


from app.tmdb import TitleDetails  # noqa: E402  (keeps tmdb as single source for schema)


async def fetch_game_details(external_id: str, settings: Settings) -> TitleDetails:
    if settings.rawg_api_key is None:
        raise RAWGError("RAWG_API_KEY is not configured")

    url = f"{settings.rawg_base_url}/games/{external_id}"
    try:
        async with httpx.AsyncClient(timeout=settings.rawg_timeout_seconds) as client:
            response = await client.get(
                url, params={"key": settings.rawg_api_key.get_secret_value()}
            )
    except httpx.HTTPError as exc:
        raise RAWGError("RAWG request failed") from exc

    if response.status_code == 404:
        raise RAWGError("Title not found")
    if response.status_code != 200:
        raise RAWGError(f"RAWG status {response.status_code}")

    payload = response.json()
    description = (payload.get("description_raw") or "").strip() or None
    return TitleDetails(
        title=payload.get("name") or "",
        original_title=None,
        description=description,
        description_language="en" if description else None,
        poster_url=payload.get("background_image") or None,
        release_date=payload.get("released") or None,
        genres=[g.get("name", "") for g in payload.get("genres", []) if g.get("name")],
        seasons_count=None,
    )
