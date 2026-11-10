"""SCRUM-26: відгуки."""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.database


def test_review_write_edit_delete_keeps_entry(
    api_client: TestClient,
    register: Callable[[], dict],
    make_title: Callable[..., UUID],
) -> None:
    """Відгук пишеться, редагується і видаляється; запис і оцінка при цьому лишаються."""
    register()
    url = f"/api/me/titles/{make_title(media_type='movie')}"

    written = api_client.patch(url, json={"review": "  Чудовий фільм  "})
    assert written.status_code == 200
    entry = written.json()["entry"]
    assert entry["status"] == "completed", "відгук без запису додає тайтл як завершений"
    assert entry["review"] == "Чудовий фільм"
    first_time = datetime.fromisoformat(entry["review_updated_at"])

    edited = api_client.patch(url, json={"review": "Перегляну ще раз"})
    assert edited.status_code == 200
    assert edited.json()["entry"]["review"] == "Перегляну ще раз"
    assert datetime.fromisoformat(edited.json()["entry"]["review_updated_at"]) >= first_time

    rated = api_client.patch(url, json={"rating": 9})
    assert rated.json()["entry"]["review"] == "Перегляну ще раз", "оцінка не стирає відгук"

    deleted = api_client.patch(url, json={"review": None})
    assert deleted.status_code == 200
    entry = api_client.get(url).json()["entry"]
    assert entry["review"] is None
    assert entry["review_updated_at"] is None
    assert (entry["status"], entry["rating"]) == ("completed", 9)
