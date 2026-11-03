from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.auth import router as auth_router
from app.config import get_settings
from app.exceptions import ApiError, api_error_handler, validation_error_handler
from app.search import router as search_router
from app.users import router as users_router

settings = get_settings()

app = FastAPI(title="MediaTrack API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(search_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
