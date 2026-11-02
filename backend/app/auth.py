from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db_session
from app.deps import get_current_user
from app.exceptions import ApiError
from app.models import User
from app.schemas import LoginInput, RegisterInput, UserResponse
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_session_cookie(response: Response, user: User, settings: Settings) -> None:
    token = create_access_token(user.id, settings)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.jwt_expires_minutes * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(
    payload: RegisterInput,
    response: Response,
    db: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserResponse:
    email_taken = db.execute(
        select(User.id).where(func.lower(User.email) == payload.email.lower())
    ).scalar_one_or_none()
    if email_taken is not None:
        raise ApiError(
            status_code=409,
            detail="Email вже зареєстрований",
            fields={"email": "Email вже зареєстрований"},
        )

    username_taken = db.execute(
        select(User.id).where(func.lower(User.username) == payload.username.lower())
    ).scalar_one_or_none()
    if username_taken is not None:
        raise ApiError(
            status_code=409,
            detail="Нікнейм вже зайнятий",
            fields={"username": "Нікнейм вже зайнятий"},
        )

    user = User(
        email=payload.email,
        username=payload.username,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    _set_session_cookie(response, user, settings)
    return UserResponse(user=user)


@router.post("/login", response_model=UserResponse)
def login(
    payload: LoginInput,
    response: Response,
    db: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserResponse:
    user = db.execute(
        select(User).where(func.lower(User.email) == payload.email.lower())
    ).scalar_one_or_none()
    if user is None or not verify_password(user.password_hash, payload.password):
        raise ApiError(status_code=401, detail="Неправильний email або пароль")

    _set_session_cookie(response, user, settings)
    return UserResponse(user=user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserResponse)
def me(user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return UserResponse(user=user)
