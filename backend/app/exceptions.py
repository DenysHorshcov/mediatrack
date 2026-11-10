"""Error format shared with the frontend: {detail, fields?}."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Формат усіх помилок API (4xx, 5xx)."""

    detail: str = Field(
        description="Повідомлення для користувача українською.",
        examples=["Перевірте правильність полів"],
    )
    fields: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Помилки окремих полів тіла запиту: назва поля → повідомлення. "
            "Буває у 400, 409 і 422; у 422 для помилок query/path-параметрів може бути порожнім."
        ),
        examples=[{"email": "Email вже зареєстрований"}],
    )


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        detail: str,
        fields: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.fields = fields or {}


async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    body: dict = {"detail": exc.detail}
    if exc.fields:
        body["fields"] = exc.fields
    return JSONResponse(status_code=exc.status_code, content=body)


_FIELD_MESSAGES_UK: dict[str, str] = {
    "value_error": "Некоректне значення",
    "string_too_short": "Значення закоротке",
    "string_too_long": "Значення задовге",
    "missing": "Поле обовʼязкове",
}


async def validation_error_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    fields: dict[str, str] = {}
    for error in exc.errors():
        location = error.get("loc", ())
        if len(location) >= 2 and location[0] == "body":
            name = str(location[1])
            fields.setdefault(
                name,
                _FIELD_MESSAGES_UK.get(error.get("type", ""), str(error.get("msg", ""))),
            )
    return JSONResponse(
        status_code=422,
        content={"detail": "Перевірте правильність полів", "fields": fields},
    )
