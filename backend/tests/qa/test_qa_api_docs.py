"""SCRUM-27: документація API (/docs, /openapi.json).

Тести не потребують БД: перевіряють, що Swagger лишається повним і точним,
бо з openapi.json генеруються типи для фронту (openapi-typescript).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

METHODS = {"get", "post", "put", "patch", "delete"}


@pytest.fixture(scope="module")
def spec() -> dict:
    with TestClient(app) as client:
        response = client.get("/openapi.json")
    assert response.status_code == 200
    return response.json()


def _operations(spec: dict):
    for path, item in spec["paths"].items():
        for method, operation in item.items():
            if method in METHODS:
                yield f"{method.upper()} {path}", operation


def test_every_endpoint_is_documented(spec: dict) -> None:
    """У кожного ендпоінта є людська назва, опис і задокументовані помилки авторизації."""
    problems = []
    for name, op in _operations(spec):
        if not op.get("summary") or op["summary"].isascii():
            problems.append(f"{name}: немає української summary")
        if not op.get("description"):
            problems.append(f"{name}: немає description")
        if op.get("security") and "401" not in op["responses"]:
            problems.append(f"{name}: захищений, але 401 не описано")
        for code, response in op["responses"].items():
            if response["description"] == "Successful Response":
                problems.append(f"{name} {code}: стандартний англійський опис відповіді")
    assert not problems, "\n".join(problems)


def test_errors_use_api_error_format(spec: dict) -> None:
    """Усі помилки описані форматом бекенду {detail, fields}, а не стандартним FastAPI."""
    schemas = spec["components"]["schemas"]
    assert "HTTPValidationError" not in schemas
    assert set(schemas["ErrorResponse"]["properties"]) == {"detail", "fields"}
    for name, op in _operations(spec):
        for code, response in op["responses"].items():
            if code.startswith(("4", "5")):
                ref = response["content"]["application/json"]["schema"]["$ref"]
                assert ref.endswith("/ErrorResponse"), f"{name} {code}: {ref}"


def test_enum_fields_are_precise_for_frontend_types(spec: dict) -> None:
    """Поля з фіксованим набором значень описані як enum, а не як довільний рядок."""
    schemas = spec["components"]["schemas"]
    media = ["movie", "series", "game"]
    statuses = ["planned", "in_progress", "completed", "on_hold", "dropped"]
    assert schemas["SearchItem"]["properties"]["type"]["enum"] == media
    assert schemas["TitleOut"]["properties"]["provider"]["enum"] == ["tmdb", "rawg"]
    assert schemas["TitleOut"]["properties"]["media_type"]["enum"] == media
    assert schemas["LibraryTitleOut"]["properties"]["media_type"]["enum"] == media
    assert schemas["LibraryTitleOut"]["properties"]["status"]["enum"] == statuses
    assert "SessionCookie" in spec["components"]["securitySchemes"]
