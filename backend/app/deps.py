from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import APIKeyCookie
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db_session
from app.exceptions import ApiError
from app.models import User
from app.security import decode_access_token


# Те саме читання cookie, що й раніше, але оголошене як схема авторизації,
# щоб у /docs захищені ендпоінти були позначені замком.
session_cookie = APIKeyCookie(
    name="mediatrack_session",
    scheme_name="SessionCookie",
    description=(
        "JWT у httpOnly-cookie `mediatrack_session`. Ставиться після "
        "POST /api/auth/register або POST /api/auth/login."
    ),
    auto_error=False,
)


def _unauthorized() -> ApiError:
    return ApiError(status_code=401, detail="Не авторизовано")


def get_current_user(
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db_session)],
    session_token: Annotated[str | None, Depends(session_cookie)],
) -> User:
    if not session_token:
        raise _unauthorized()
    try:
        payload = decode_access_token(session_token, settings)
    except jwt.PyJWTError as exc:
        raise _unauthorized() from exc
    sub = payload.get("sub")
    if not isinstance(sub, str):
        raise _unauthorized()
    try:
        user_id = UUID(sub)
    except ValueError as exc:
        raise _unauthorized() from exc
    user = db.get(User, user_id)
    if user is None:
        raise _unauthorized()
    return user
