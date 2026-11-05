"""Games provider backed by the Steam Store API.

Steam's storefront exposes two undocumented-but-stable endpoints that work
without an API key:

    GET https://store.steampowered.com/api/storesearch/?term=<q>&cc=US&l=english
    GET https://store.steampowered.com/api/appdetails?appids=<id>&l=english

We keep the module name `rawg` and the provider label `rawg` in the DB check
constraint so the rest of the stack is untouched.  Posters come from Steam's
library capsule CDN at a 2:3 aspect ratio that matches our card layout.
"""

from __future__ import annotations

import re

import httpx

from app.config import Settings
from app.tmdb import SearchItem, TitleDetails


class RAWGError(Exception):
    """Raised when the Steam store cannot answer. Mapped to 503 at the router."""


_SEARCH_PATH = "/storesearch/"
_DETAILS_PATH = "/appdetails"
_LIBRARY_CAPSULE = "https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/library_600x900.jpg"
_HTML_TAG = re.compile(r"<[^>]+>")
_YEAR = re.compile(r"\b(19|20)\d{2}\b")


def _poster(appid: int | str, fallback: str | None) -> str | None:
    if not appid:
        return fallback
    return _LIBRARY_CAPSULE.format(appid=appid)


def _year(value: str | None) -> int | None:
    if not value:
        return None
    match = _YEAR.search(value)
    return int(match.group(0)) if match else None


def _release_date(value: str | None) -> str | None:
    """Try to coax Steam's free-form release strings into an ISO date."""

    if not value:
        return None
    # Try common formats: "May 18, 2015", "18 May, 2015", "2015-05-18".
    from datetime import datetime

    for fmt in ("%b %d, %Y", "%d %b, %Y", "%B %d, %Y", "%d %B, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    # Fall back to just the year, formatted as YYYY-01-01.
    year = _year(value)
    return f"{year}-01-01" if year else None


def _strip_html(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = _HTML_TAG.sub("", value)
    cleaned = cleaned.replace("&nbsp;", " ").replace("&amp;", "&")
    cleaned = cleaned.replace("&lt;", "<").replace("&gt;", ">")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or None


_NOISE_PATTERNS = re.compile(
    r"\b(soundtrack|ost|demo|dlc|artbook|art book|wallpapers?)\b",
    re.IGNORECASE,
)


def _is_noise(name: str) -> bool:
    return bool(_NOISE_PATTERNS.search(name))


def _map_search_item(item: dict) -> SearchItem | None:
    appid = item.get("id")
    name = item.get("name")
    if not appid or not name:
        return None
    if _is_noise(name):
        return None
    release = item.get("release_date") if isinstance(item.get("release_date"), str) else None
    return SearchItem(
        id=str(appid),
        type="game",
        title=name,
        year=_year(release),
        poster=_poster(appid, item.get("tiny_image")),
    )


async def _get(url: str, settings: Settings, params: dict) -> dict | list:
    headers = {
        "Accept": "application/json",
        "User-Agent": "MediaTrack/0.1 (student project)",
    }
    try:
        async with httpx.AsyncClient(
            timeout=settings.rawg_timeout_seconds, headers=headers
        ) as client:
            response = await client.get(url, params=params)
    except httpx.HTTPError as exc:
        raise RAWGError("Steam store request failed") from exc

    if response.status_code == 404:
        raise RAWGError("Not found")
    if response.status_code != 200:
        raise RAWGError(f"Steam store status {response.status_code}")

    try:
        return response.json()
    except ValueError as exc:
        raise RAWGError("Steam store returned non-JSON") from exc


async def search_games(query: str, settings: Settings) -> list[SearchItem]:
    query = query.strip()
    if not query:
        return []

    payload = await _get(
        f"{settings.rawg_base_url}{_SEARCH_PATH}",
        settings,
        {
            "term": query,
            "cc": "US",
            "l": "english",
        },
    )
    if not isinstance(payload, dict):
        return []
    items: list[SearchItem] = []
    for raw in payload.get("items", []):
        mapped = _map_search_item(raw)
        if mapped is not None:
            items.append(mapped)
        if len(items) >= settings.rawg_page_size:
            break
    return items


def _extract_details(
    payload: object, external_id: str, language: str
) -> TitleDetails:
    if not isinstance(payload, dict):
        raise RAWGError("Unexpected Steam response")
    wrapper = payload.get(str(external_id)) or {}
    if not wrapper.get("success"):
        raise RAWGError("Title not found")
    data = wrapper.get("data") or {}
    if not data.get("name"):
        raise RAWGError("Title not found")

    description = (
        _strip_html(data.get("short_description"))
        or _strip_html(data.get("detailed_description"))
    )
    release_raw = (data.get("release_date") or {}).get("date")

    return TitleDetails(
        title=data["name"],
        original_title=None,
        description=description,
        description_language=language if description else None,
        poster_url=_poster(external_id, data.get("header_image")),
        release_date=_release_date(release_raw),
        genres=[g.get("description", "") for g in data.get("genres", []) if g.get("description")],
        seasons_count=None,
    )


async def fetch_game_details(external_id: str, settings: Settings) -> TitleDetails:
    if not external_id.isdigit():
        raise RAWGError("Invalid Steam appid")

    url = f"{settings.rawg_base_url}{_DETAILS_PATH}"
    uk_payload = await _get(url, settings, {"appids": external_id, "l": "ukrainian"})
    details = _extract_details(uk_payload, external_id, "uk")

    if details.description is None:
        try:
            en_payload = await _get(
                url, settings, {"appids": external_id, "l": "english"}
            )
            en_details = _extract_details(en_payload, external_id, "en")
        except RAWGError:
            return details
        if en_details.description:
            details.description = en_details.description
            details.description_language = "en"
    return details
