"""SCRUM-69: оцінки тайтлів (1–10)."""

from collections.abc import Callable
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.database


def test_rating_without_entry_adds_title_as_completed(
    api_client: TestClient,
    register: Callable[[], dict],
    make_title: Callable[..., UUID],
) -> None:
    """Оцінка тайтлу, якого ще немає у списках, додає його зі статусом «Завершено»."""
    register()
    title_id = str(make_title(media_type="movie"))

    response = api_client.patch(f"/api/me/titles/{title_id}", json={"rating": 8})

    assert response.status_code == 200
    entry = response.json()["entry"]
    assert entry["status"] == "completed"
    assert entry["rating"] == 8
    listed = api_client.get("/api/me/titles").json()["items"]
    assert [(i["id"], i["rating"]) for i in listed] == [(title_id, 8)]


def test_rating_accepts_only_1_to_10(
    api_client: TestClient,
    register: Callable[[], dict],
    make_title: Callable[..., UUID],
) -> None:
    """Межі оцінки: 0 і 11 відхиляються, 1 і 10 приймаються, статус не змінюється."""
    register()
    title_id = str(make_title(media_type="series"))
    assert (
        api_client.put(f"/api/me/titles/{title_id}", json={"status": "planned"}).status_code
        == 200
    )

    for invalid in (0, 11):
        rejected = api_client.patch(f"/api/me/titles/{title_id}", json={"rating": invalid})
        assert rejected.status_code == 422, invalid
        assert rejected.json()["fields"]["rating"]

    for valid in (1, 10):
        accepted = api_client.patch(f"/api/me/titles/{title_id}", json={"rating": valid})
        assert accepted.status_code == 200, valid
        assert accepted.json()["entry"]["rating"] == valid
        assert accepted.json()["entry"]["status"] == "planned"
