from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from app.api_docs import API_DESCRIPTION, OPENAPI_TAGS
from app.auth import router as auth_router
from app.config import get_settings
from app.exceptions import ApiError, api_error_handler, validation_error_handler
from app.frontend import mount_frontend
from app.library import router as library_router
from app.search import router as search_router
from app.stats import router as stats_router
from app.titles import router as titles_router
from app.users import router as users_router

settings = get_settings()

app = FastAPI(
    title="MediaTrack API",
    version="0.1.0",
    description=API_DESCRIPTION,
    openapi_tags=OPENAPI_TAGS,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)

SUCCESS_DESCRIPTION = "Успішна відповідь"

for router in (
    auth_router,
    users_router,
    search_router,
    titles_router,
    library_router,
    stats_router,
):
    # Український підпис для успішних відповідей у /docs замість "Successful Response".
    for route in router.routes:
        if isinstance(route, APIRoute) and route.response_description == "Successful Response":
            route.response_description = SUCCESS_DESCRIPTION
    app.include_router(router)


@app.get(
    "/api/health",
    tags=["system"],
    summary="Перевірка, що сервіс живий",
    response_description=SUCCESS_DESCRIPTION,
    description="Завжди повертає `{\"status\": \"ok\"}`. Використовується health check на Render.",
)
def health() -> dict[str, str]:
    return {"status": "ok"}


mount_frontend(app, settings.frontend_dist_dir)
