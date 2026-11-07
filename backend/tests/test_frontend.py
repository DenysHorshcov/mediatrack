from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.frontend import mount_frontend


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<div id=root></div>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (dist / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("nope", encoding="utf-8")

    app = FastAPI()

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/login")
    def login() -> dict[str, str]:
        return {"ok": "yes"}

    assert mount_frontend(app, dist)
    return TestClient(app)


@pytest.mark.parametrize("path", ["/", "/search", "/title/tmdb/movie/550"])
def test_spa_paths_return_index(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert "id=root" in response.text
    assert response.headers["cache-control"] == "no-cache"


def test_static_files_are_served(client: TestClient) -> None:
    assert client.get("/assets/app.js").text == "console.log(1)"
    assert client.get("/favicon.svg").text == "<svg/>"


def test_missing_asset_is_404(client: TestClient) -> None:
    assert client.get("/assets/missing.js").status_code == 404


def test_api_routes_still_work(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok"}


@pytest.mark.parametrize("method", ["GET", "POST", "DELETE"])
def test_unknown_api_path_is_json_404(client: TestClient, method: str) -> None:
    response = client.request(method, "/api/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_wrong_method_on_api_route_is_405(client: TestClient) -> None:
    assert client.get("/api/login").status_code == 405


def test_path_traversal_is_blocked(client: TestClient) -> None:
    response = client.get("/..%2Fsecret.txt")
    assert "nope" not in response.text


def test_missing_build_is_not_mounted(tmp_path: Path) -> None:
    assert mount_frontend(FastAPI(), tmp_path / "missing") is False
