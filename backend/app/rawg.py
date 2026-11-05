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
