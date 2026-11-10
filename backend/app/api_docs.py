"""Спільні шматки OpenAPI-документації (/docs): опис API, теги, помилки."""

from typing import Any

from app.exceptions import ErrorResponse

API_DESCRIPTION = """
API MediaTrack — облік фільмів, серіалів та ігор.

**Авторизація.** Сесія — JWT у httpOnly-cookie `mediatrack_session`. Її ставлять
`POST /api/auth/register` і `POST /api/auth/login`, прибирає `POST /api/auth/logout`.
Щоб пробувати захищені запити тут, у Swagger, спершу виконайте login: браузер збереже
cookie і сам відправлятиме її з наступними запитами. Кнопка **Authorize** для cookie
в браузері не працює — це обмеження браузерів.

**Помилки** завжди мають формат `{"detail": "...", "fields": {"поле": "..."}}`
(див. схему `ErrorResponse`). `fields` є лише там, де помилка стосується конкретних полів.

**Джерела даних.** Фільми й серіали — TMDB (`provider = tmdb`), ігри — Steam Store API
(`provider = rawg`: назва провайдера лишилась від RAWG, щоб не міняти схему БД).
"""

OPENAPI_TAGS = [
    {"name": "auth", "description": "Реєстрація, вхід, вихід, поточний користувач."},
    {"name": "users", "description": "Профіль поточного користувача."},
    {"name": "search", "description": "Пошук фільмів і серіалів у TMDB та ігор у Steam."},
    {
        "name": "titles",
        "description": "Картка тайтлу. Перше відкриття тягне дані з TMDB/Steam і зберігає в БД.",
    },
    {
        "name": "library",
        "description": "Мої списки: статус, оцінка, відгук і прогрес серій для тайтлів.",
    },
    {"name": "stats", "description": "Статистика поточного користувача для профілю."},
    {"name": "system", "description": "Службові ендпоінти."},
]


def error(description: str, detail: str, fields: dict[str, str] | None = None) -> dict[str, Any]:
    """Опис однієї помилкової відповіді у форматі ErrorResponse з прикладом."""
    example: dict[str, Any] = {"detail": detail}
    if fields:
        example["fields"] = fields
    return {
        "model": ErrorResponse,
        "description": description,
        "content": {"application/json": {"example": example}},
    }


SESSION_COOKIE_HEADER = {
    "Set-Cookie": {
        "description": "Cookie сесії `mediatrack_session` (httpOnly, JWT).",
        "schema": {"type": "string"},
    }
}

UNAUTHORIZED: dict[int | str, dict[str, Any]] = {
    401: error(
        "Немає cookie сесії або вона недійсна. Виконайте login або register.",
        "Не авторизовано",
    )
}

VALIDATION: dict[int | str, dict[str, Any]] = {
    422: error(
        "Некоректні параметри або тіло запиту.",
        "Перевірте правильність полів",
        {"email": "Некоректне значення"},
    )
}
