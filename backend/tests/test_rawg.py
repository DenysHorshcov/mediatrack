import asyncio

import httpx
import pytest
import respx

from app import rawg
from app.config import Settings


BASE = "https://store.steampowered.com/api"


def _settings() -> Settings:
    return Settings()


# --- Pure helpers --------------------------------------------------------


def test_poster_uses_steam_library_capsule() -> None:
    url = rawg._poster(292030, None)
    assert url == "https://cdn.cloudflare.steamstatic.com/steam/apps/292030/library_600x900.jpg"


def test_poster_falls_back_when_appid_is_falsy() -> None:
    assert rawg._poster(0, None) is None
    assert rawg._poster(0, "fallback.jpg") == "fallback.jpg"


def test_year_finds_four_digit_year() -> None:
    assert rawg._year(None) is None
    assert rawg._year("Coming soon") is None
    assert rawg._year("May 18, 2015") == 2015
    assert rawg._year("Q4 2024") == 2024


def test_release_date_parses_common_steam_formats() -> None:
    assert rawg._release_date("May 18, 2015") == "2015-05-18"
    assert rawg._release_date("18 May, 2015") == "2015-05-18"
    assert rawg._release_date("2022-02-25") == "2022-02-25"
    # Fallback to year-01-01 when the format is unknown.
    assert rawg._release_date("Q4 2024") == "2024-01-01"
    assert rawg._release_date("TBA") is None


def test_strip_html_cleans_description() -> None:
    raw = "<p>Line one.</p>&nbsp;<strong>Line&nbsp;two.</strong>"
    assert rawg._strip_html(raw) == "Line one. Line two."
    assert rawg._strip_html(None) is None
    assert rawg._strip_html("   ") is None


def test_map_search_item_skips_items_without_id_or_name() -> None:
    assert rawg._map_search_item({}) is None
    assert rawg._map_search_item({"id": 1}) is None
    assert rawg._map_search_item({"name": "Nope"}) is None


def test_map_search_item_fills_fields() -> None:
    item = rawg._map_search_item(
        {
            "id": 292030,
            "name": "The Witcher 3: Wild Hunt",
            "release_date": "May 18, 2015",
            "tiny_image": "https://example/tiny.jpg",
        }
    )
    assert item is not None
    assert item.id == "292030"
    assert item.type == "game"
    assert item.title == "The Witcher 3: Wild Hunt"
    assert item.year == 2015
    assert "library_600x900" in (item.poster or "")


# --- Search over HTTP (mocked) -------------------------------------------


@respx.mock
def test_search_returns_mapped_items() -> None:
    respx.get(f"{BASE}/storesearch/").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {"id": 292030, "name": "The Witcher 3", "release_date": "May 18, 2015"},
                    {"id": 578080, "name": "PUBG", "release_date": "Dec 21, 2017"},
                    {},  # dropped
                ]
            },
        )
    )

    results = asyncio.run(rawg.search_games("witcher", _settings()))
    assert [item.title for item in results] == ["The Witcher 3", "PUBG"]
    assert [item.id for item in results] == ["292030", "578080"]


@respx.mock
def test_search_respects_page_size() -> None:
    items = [{"id": i, "name": f"Game {i}"} for i in range(1, 100)]
    respx.get(f"{BASE}/storesearch/").mock(
        return_value=httpx.Response(200, json={"items": items})
    )

    settings = Settings(rawg_page_size=5)
    results = asyncio.run(rawg.search_games("anything", settings))
    assert len(results) == 5


@respx.mock
def test_search_wraps_http_error_as_rawg_error() -> None:
    respx.get(f"{BASE}/storesearch/").mock(
        return_value=httpx.Response(500, text="boom")
    )
    with pytest.raises(rawg.RAWGError):
        asyncio.run(rawg.search_games("x", _settings()))


@respx.mock
def test_search_wraps_transport_error() -> None:
    respx.get(f"{BASE}/storesearch/").mock(side_effect=httpx.ConnectError("down"))
    with pytest.raises(rawg.RAWGError):
        asyncio.run(rawg.search_games("x", _settings()))


def test_search_short_circuits_on_empty_query() -> None:
    result = asyncio.run(rawg.search_games("   ", _settings()))
    assert result == []


# --- Details over HTTP (mocked) -------------------------------------------


@respx.mock
def test_fetch_game_details_maps_response() -> None:
    respx.get(f"{BASE}/appdetails").mock(
        return_value=httpx.Response(
            200,
            json={
                "292030": {
                    "success": True,
                    "data": {
                        "name": "The Witcher 3: Wild Hunt",
                        "short_description": "<p>Monster hunter in a huge world.</p>",
                        "header_image": "https://steam/header.jpg",
                        "release_date": {"date": "May 18, 2015"},
                        "genres": [
                            {"id": "3", "description": "RPG"},
                            {"id": "25", "description": "Adventure"},
                        ],
                    },
                }
            },
        )
    )

    details = asyncio.run(rawg.fetch_game_details("292030", _settings()))
    assert details.title == "The Witcher 3: Wild Hunt"
    assert details.description == "Monster hunter in a huge world."
    assert details.description_language == "uk"
    assert details.release_date == "2015-05-18"
    assert details.genres == ["RPG", "Adventure"]
    assert "library_600x900" in (details.poster_url or "")


@respx.mock
def test_fetch_game_details_falls_back_to_english_when_uk_is_blank() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        lang = request.url.params.get("l")
        if lang == "ukrainian":
            return httpx.Response(
                200,
                json={
                    "292030": {
                        "success": True,
                        "data": {
                            "name": "The Witcher 3",
                            "short_description": "",
                        },
                    }
                },
            )
        return httpx.Response(
            200,
            json={
                "292030": {
                    "success": True,
                    "data": {
                        "name": "The Witcher 3",
                        "short_description": "Monster hunter in a huge world.",
                    },
                }
            },
        )

    respx.get(f"{BASE}/appdetails").mock(side_effect=respond)

    details = asyncio.run(rawg.fetch_game_details("292030", _settings()))
    assert details.description == "Monster hunter in a huge world."
    assert details.description_language == "en"


@respx.mock
def test_fetch_game_details_raises_when_success_false() -> None:
    respx.get(f"{BASE}/appdetails").mock(
        return_value=httpx.Response(200, json={"1": {"success": False}})
    )
    with pytest.raises(rawg.RAWGError):
        asyncio.run(rawg.fetch_game_details("1", _settings()))


def test_fetch_game_details_rejects_non_numeric_id() -> None:
    with pytest.raises(rawg.RAWGError):
        asyncio.run(rawg.fetch_game_details("abc", _settings()))
