from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api_docs import UNAUTHORIZED, VALIDATION, error
from app.database import get_db_session
from app.deps import get_current_user
from app.exceptions import ApiError
from app.models import User
from app.schemas import UserResponse

router = APIRouter(prefix="/api/users", tags=["users"])


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
        description=(
            "Новий нікнейм, до 30 символів; пробіли по краях обрізаються. "
            "Порожній або з самих пробілів — 422."
        ),
        examples=["olena_k"],
    )
    avatar_url: str | None = Field(
        default=None,
        max_length=2048,
        description="Посилання на аватар. null або порожній рядок прибирає аватар.",
        examples=["https://example.com/avatar.png"],
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Мій профіль",
    description="Те саме, що `GET /api/auth/me`; використовується сторінкою профілю.",
    responses={**UNAUTHORIZED},
)
def get_me(user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return UserResponse(user=user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Змінити профіль",
    description=(
        "Змінює лише передані поля (`username`, `avatar_url`); невідомі поля — 422. "
        "Нікнейм унікальний без урахування регістру."
    ),
    responses={
        **UNAUTHORIZED,
        409: error(
            "Нікнейм уже зайнятий іншим користувачем.",
            "Нікнейм вже зайнятий",
            {"username": "Нікнейм вже зайнятий"},
        ),
        **VALIDATION,
    },
)
def update_me(
    payload: ProfileUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> UserResponse:
    data = payload.model_dump(exclude_unset=True)

    if "username" in data:
        new_username = (data["username"] or "").strip()
        if not new_username:
            raise ApiError(
                status_code=422,
                detail="Перевірте правильність полів",
                fields={"username": "Нікнейм не може бути порожнім"},
            )
        if new_username.lower() != user.username.lower():
            taken = db.execute(
                select(User.id).where(
                    func.lower(User.username) == new_username.lower(),
                    User.id != user.id,
                )
            ).scalar_one_or_none()
            if taken is not None:
                raise ApiError(
                    status_code=409,
                    detail="Нікнейм вже зайнятий",
                    fields={"username": "Нікнейм вже зайнятий"},
                )
        user.username = new_username

    if "avatar_url" in data:
        value = (data["avatar_url"] or "").strip() or None
        user.avatar_url = value

    db.commit()
    db.refresh(user)
    return UserResponse(user=user)
