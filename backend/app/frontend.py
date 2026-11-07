"""Serve the built React app (frontend/dist) from the same service as the API.

Unknown GET paths outside /api return index.html so React Router deep links
work. API routes and their errors are untouched: the fallback only runs when
no route matched and the path is not under /api.
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

# Paths that must keep normal 404s instead of getting index.html.
_RESERVED_PREFIXES = ("/api", "/assets", "/docs", "/redoc", "/openapi.json")


def _is_reserved(path: str) -> bool:
    return any(path == p or path.startswith(p + "/") for p in _RESERVED_PREFIXES)


def mount_frontend(app: FastAPI, dist_dir: Path) -> bool:
    """Serve dist_dir if it holds a build. Returns True when mounted."""
    dist_dir = dist_dir.resolve()
    index_file = dist_dir / "index.html"
    if not index_file.is_file():
        return False

    assets_dir = dist_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    async def spa_fallback(
        request: Request, exc: StarletteHTTPException
    ) -> Response:
        path = request.url.path
        if (
            exc.status_code != 404
            or request.method not in {"GET", "HEAD"}
            or _is_reserved(path)
        ):
            return await http_exception_handler(request, exc)

        # Root-level files from the build (favicon etc.), never outside dist.
        candidate = (dist_dir / path.lstrip("/")).resolve()
        if candidate != dist_dir and candidate.is_relative_to(dist_dir) and candidate.is_file():
            return FileResponse(candidate)

        return FileResponse(index_file, headers={"Cache-Control": "no-cache"})

    app.add_exception_handler(StarletteHTTPException, spa_fallback)
    return True
