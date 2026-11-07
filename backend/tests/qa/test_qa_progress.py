"""SCRUM-69: прогрес серій (сезони звіряються з TMDB, замоканим через respx)."""

from collections.abc import Callable
from uuid import UUID

import pytest
import respx
from fastapi.testclient import TestClient

from tests.qa.conftest import TMDB_BASE_URL, TMDB_TEST_KEY, random_external_id

pytestmark = pytest.mark.database

# Сезон 0 — «спецвипуски» в TMDB, бек його ігнорує.
SEASONS = {
    "seasons": [
        {"season_number": 0, "episode_count": 3, "name": "Спецвипуски"},
        {"season_number": 1, "episode_count": 10, "name": "Сезон 1"},
        {"season_number": 2, "episode_count": 8, "name": "Сезон 2"},
    ]
}


def test_valid_progress_is_saved(
    api_client: TestClient,
    external_api: respx.MockRouter,
    register: Callable[[], dict],
    make_title: Callable[..., UUID],
) -> None:
    """Сезон і епізод, що існують у TMDB, зберігаються, тайтл стає «Дивлюсь»."""
    register()
    series_id = random_external_id()
    title_id = str(make_title(media_type="series", external_id=series_id))
    route = external_api.get(f"{TMDB_BASE_URL}/tv/{series_id}").respond(200, json=SEASONS)

    response = api_client.patch(
        f"/api/me/titles/{title_id}", json={"season": 2, "episode": 8}
    )

    assert response.status_code == 200
    entry = response.json()["entry"]
    assert (entry["status"], entry["current_season"], entry["current_episode"]) == (
        "in_progress",
        2,
        8,
    )
    saved = api_client.get(f"/api/me/titles/{title_id}").json()["entry"]
    assert (saved["current_season"], saved["current_episode"]) == (2, 8)
    assert route.calls.last.request.url.params["api_key"] == TMDB_TEST_KEY


def test_invalid_progress_is_rejected_and_old_progress_kept(
    api_client: TestClient,
    external_api: respx.MockRouter,
    register: Callable[[], dict],
    make_title: Callable[..., UUID],
) -> None:
    """Неіснуючий сезон чи епізод дає 400 з поясненням, збережений прогрес не змінюється."""
    register()
    series_id = random_external_id()
    title_id = str(make_title(media_type="series", external_id=series_id))
    external_api.get(f"{TMDB_BASE_URL}/tv/{series_id}").respond(200, json=SEASONS)
    url = f"/api/me/titles/{title_id}"
    assert api_client.patch(url, json={"season": 1, "episode": 3}).status_code == 200

    no_season = api_client.patch(url, json={"season": 3, "episode": 1})
    assert no_season.status_code == 400
    assert no_season.json()["fields"] == {"season": "Такого сезону немає"}

    no_episode = api_client.patch(url, json={"season": 2, "episode": 9})
    assert no_episode.status_code == 400
    assert no_episode.json()["fields"] == {"episode": "У сезоні лише 8 епізодів"}

    specials = api_client.patch(url, json={"season": 0, "episode": 1})
    assert specials.status_code == 422

    entry = api_client.get(url).json()["entry"]
    assert (entry["current_season"], entry["current_episode"]) == (1, 3)
